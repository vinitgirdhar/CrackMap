"""CrackMap pothole training pipeline.

Three steps, run in order:

    python train_potholes.py autolabel   # 1. generate boxes to review
    #    -> review + correct labels in a tool (see REVIEW.md)
    python train_potholes.py train       # 2. fine-tune YOLOv8 on reviewed data
    python train_potholes.py compare     # 3. before/after on your own images
"""

import argparse
import sys
from pathlib import Path

from src.config import MODELS_DIR, PROJECT_ROOT

DEFAULT_IMAGES = PROJECT_ROOT / "data" / "real_potholes" / "JPEGImages"
DEFAULT_LABELS = PROJECT_ROOT / "data" / "real_potholes" / "labels"
DEFAULT_DATASET = PROJECT_ROOT / "data" / "yolo_dataset"


def cmd_autolabel(args: argparse.Namespace) -> int:
    from src.models.autolabel import generate_pseudo_labels

    images = Path(args.images)
    labels = Path(args.labels)
    if not images.exists():
        print(f"ERROR: image folder not found: {images}")
        return 1

    print(f"Auto-labelling {images} at conf={args.conf} (low on purpose: over-propose)")
    stats = generate_pseudo_labels(images, labels, conf_threshold=args.conf, overwrite=args.overwrite)

    print(
        f"\n  images found     : {stats['images']}\n"
        f"  labelled         : {stats['labelled']}\n"
        f"  already had label: {stats['skipped']} (use --overwrite to redo)\n"
        f"  boxes proposed   : {stats['boxes']}\n"
        f"  images with none : {stats['empty']}"
    )
    print(f"\nLabels written to: {labels}")
    print("NEXT: review them (see REVIEW.md), then run:  python train_potholes.py train")
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    from src.models.yolo_finetune import build_yolo_dataset, finetune_yolo

    images, labels = Path(args.images), Path(args.labels)
    if not labels.exists() or not any(labels.glob("*.txt")):
        print(f"ERROR: no label files in {labels}. Run 'autolabel' first, then review them.")
        return 1

    print("Building dataset...")
    ds = build_yolo_dataset(images, labels, Path(args.dataset), val_split=args.val_split)
    print(
        f"  train images    : {ds['train_images']}\n"
        f"  val images      : {ds['val_images']}\n"
        f"  with boxes      : {ds['with_boxes']}\n"
        f"  empty negatives : {ds['empty_negatives']}\n"
        f"  unlabelled skip : {ds['skipped_unlabelled']}"
    )

    if ds["with_boxes"] == 0:
        print("ERROR: every label file is empty - nothing to learn from.")
        return 1

    # Silently training on a fraction of the folder wastes a full run and
    # produces metrics identical to the previous one, which is easy to
    # misread as "training had no effect". Make it impossible to miss.
    skipped = ds["skipped_unlabelled"]
    if skipped:
        used = ds["train_images"] + ds["val_images"]
        print(
            f"\n{'!' * 62}\n"
            f"WARNING: {skipped} image(s) have NO label file and are EXCLUDED.\n"
            f"         Training on {used} of {used + skipped} images in the folder.\n"
            f"         Run this first to label the new images:\n"
            f"             python train_potholes.py autolabel\n"
            f"{'!' * 62}"
        )
        if skipped > used and not args.allow_partial:
            print(
                "\nABORTED: more images are unlabelled than labelled, so this run\n"
                "would ignore most of your data. Run 'autolabel', or pass\n"
                "--allow-partial to train on the labelled subset anyway."
            )
            return 1

    print(f"\nFine-tuning YOLOv8 for {args.epochs} epochs...")
    res = finetune_yolo(
        ds["data_yaml"],
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        progress_callback=lambda e, l, t: print(f"  epoch {e}/{t}  loss={l:.4f}", flush=True),
    )
    print(f"\nDone on {res['device']}. Metrics: {res['metrics']}")
    print(f"Weights published to: {res['weights_path']}")
    print("The app picks these up automatically on next backend restart.")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Score stock vs fine-tuned weights on the same images."""
    import shutil
    import cv2
    import numpy as np
    from PIL import Image
    from src.models.advanced_detector import AdvancedRoadDamageDetector

    finetuned = MODELS_DIR / "pothole_yolov8_finetuned.pt"
    if not finetuned.exists():
        print(f"No fine-tuned weights at {finetuned}. Run 'train' first.")
        return 1

    all_images = sorted(Path(args.images).glob("*.jpg"))
    if not all_images:
        print(f"No images in {args.images}")
        return 1

    # Spread the sample across the folder instead of taking the first N, which
    # would only ever show alphabetically-adjacent (often near-duplicate) shots.
    step = max(1, len(all_images) // args.limit)
    images = all_images[::step][: args.limit]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    def run(tag: str) -> dict:
        det = AdvancedRoadDamageDetector()
        counts = {}
        for p in images:
            img = np.array(Image.open(p).convert("RGB"))
            res = det.predict(img, custom_conf_threshold=args.conf)
            counts[p.name] = len(res.boxes)
            cv2.imwrite(
                str(out_dir / f"{p.stem}__{tag}.jpg"),
                cv2.cvtColor(res.image, cv2.COLOR_RGB2BGR),
            )
        return counts

    print("Running fine-tuned weights...")
    ft_counts = run("finetuned")

    # Hide the fine-tuned checkpoint so the detector falls back to the stock
    # pretrained backbones, then restore it no matter what happens.
    stash = MODELS_DIR / "_stashed_finetuned.pt"
    print("Running stock pretrained weights...")
    shutil.move(str(finetuned), str(stash))
    try:
        stock_counts = run("stock")
    finally:
        shutil.move(str(stash), str(finetuned))

    print(f"\n{'image':>16} {'stock':>7} {'finetuned':>11}  delta")
    total_stock = total_ft = 0
    for name in sorted(ft_counts):
        s, f = stock_counts[name], ft_counts[name]
        total_stock += s
        total_ft += f
        print(f"{name:>16} {s:>7} {f:>11}  {f - s:+d}")
    print(f"{'TOTAL':>16} {total_stock:>7} {total_ft:>11}  {total_ft - total_stock:+d}")

    print(
        "\nBox counts alone do not prove quality - more boxes can mean more "
        "false positives. Compare the paired images side by side:"
    )
    print(f"  {out_dir.resolve()}   (*__stock.jpg vs *__finetuned.jpg)")
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    """Render label overlays so the auto-generated boxes can be eyeballed."""
    import cv2
    import numpy as np
    from PIL import Image

    images, labels = Path(args.images), Path(args.labels)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    picked = sorted(images.glob("*.jpg"))
    if not picked:
        print(f"No images in {images}")
        return 1
    step = max(1, len(picked) // args.limit)
    picked = picked[::step][: args.limit]

    for img_path in picked:
        label_path = labels / f"{img_path.stem}.txt"
        img = cv2.cvtColor(np.array(Image.open(img_path).convert("RGB")), cv2.COLOR_RGB2BGR)
        h, w = img.shape[:2]
        count = 0
        if label_path.exists():
            for line in label_path.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                xc, yc, bw, bh = (float(v) for v in parts[1:5])
                x1, y1 = int((xc - bw / 2) * w), int((yc - bh / 2) * h)
                x2, y2 = int((xc + bw / 2) * w), int((yc + bh / 2) * h)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), max(1, min(h, w) // 480))
                count += 1
        cv2.imwrite(str(out / f"{img_path.stem}_labels.jpg"), img)
        print(f"  {img_path.name:>16}  {count} boxes")

    print(f"\nPreviews written to: {out.resolve()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CrackMap pothole training pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_auto = sub.add_parser("autolabel", help="generate reviewable YOLO labels")
    p_auto.add_argument("--images", default=str(DEFAULT_IMAGES))
    p_auto.add_argument("--labels", default=str(DEFAULT_LABELS))
    p_auto.add_argument("--conf", type=float, default=0.12)
    p_auto.add_argument("--overwrite", action="store_true")
    p_auto.set_defaults(func=cmd_autolabel)

    p_train = sub.add_parser("train", help="fine-tune YOLOv8 on reviewed labels")
    p_train.add_argument("--images", default=str(DEFAULT_IMAGES))
    p_train.add_argument("--labels", default=str(DEFAULT_LABELS))
    p_train.add_argument("--dataset", default=str(DEFAULT_DATASET))
    p_train.add_argument("--epochs", type=int, default=60)
    p_train.add_argument("--imgsz", type=int, default=640)
    p_train.add_argument(
        "--batch", type=int, default=None,
        help="batch size (default: sized automatically from free VRAM)"
    )
    p_train.add_argument("--val-split", type=float, default=0.2)
    p_train.add_argument(
        "--workers",
        type=int,
        default=None,
        help="dataloader workers (default: 2 on Windows to avoid memory pressure)",
    )
    p_train.add_argument(
        "--allow-partial",
        action="store_true",
        help="train even if most images in the folder are unlabelled",
    )
    p_train.set_defaults(func=cmd_train)

    p_prev = sub.add_parser("preview", help="render label overlays to inspect them")
    p_prev.add_argument("--images", default=str(DEFAULT_IMAGES))
    p_prev.add_argument("--labels", default=str(DEFAULT_LABELS))
    p_prev.add_argument("--out", default=str(PROJECT_ROOT / "data" / "label_preview"))
    p_prev.add_argument("--limit", type=int, default=12)
    p_prev.set_defaults(func=cmd_preview)

    p_cmp = sub.add_parser("compare", help="A/B stock vs fine-tuned weights")
    p_cmp.add_argument("--images", default=str(DEFAULT_IMAGES))
    p_cmp.add_argument("--out", default=str(PROJECT_ROOT / "data" / "compare_out"))
    p_cmp.add_argument("--limit", type=int, default=12)
    p_cmp.add_argument("--conf", type=float, default=0.25)
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
