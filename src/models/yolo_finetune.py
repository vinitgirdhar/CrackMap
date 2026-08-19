"""YOLOv8 fine-tuning on reviewed pothole data.

This is the training path that actually affects what the app detects: the
inference detector loads YOLO weights, so fine-tuning YOLO (rather than the
separate Faster R-CNN in train.py) is what changes results in the UI.
"""

import random
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.config import MODELS_DIR
from src.models.autolabel import IMAGE_SUFFIXES, POTHOLE_CLASS_NAME

# Where the fine-tuned weights land. AdvancedRoadDamageDetector prefers this
# file over the stock pretrained backbones when it exists.
FINETUNED_WEIGHTS_NAME = "pothole_yolov8_finetuned.pt"


def build_yolo_dataset(
    image_dir: Path | str,
    label_dir: Path | str,
    output_dir: Path | str,
    val_split: float = 0.2,
    seed: int = 42,
    include_empty: bool = True,
) -> Dict[str, Any]:
    """Assemble an Ultralytics-format dataset from images + YOLO label files.

    Args:
        image_dir: Source images.
        label_dir: Matching .txt labels (same stem).
        output_dir: Dataset root to create (images/ and labels/ subtrees).
        val_split: Fraction held out for validation.
        seed: RNG seed so the split is reproducible across runs.
        include_empty: Keep images with no boxes as negative examples. These
            teach the model what clean pavement looks like and materially cut
            false positives, so they are kept by default.

    Returns:
        Summary including the path of the generated data.yaml.
    """
    image_dir, label_dir, output_dir = Path(image_dir), Path(label_dir), Path(output_dir)

    pairs: List[tuple] = []
    skipped_unlabelled = 0
    for img in sorted(p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES):
        lbl = label_dir / f"{img.stem}.txt"
        if not lbl.exists():
            skipped_unlabelled += 1
            continue
        has_boxes = bool(lbl.read_text(encoding="utf-8").strip())
        if not has_boxes and not include_empty:
            continue
        pairs.append((img, lbl, has_boxes))

    if not pairs:
        raise ValueError(
            f"No labelled images found. Expected .txt files in {label_dir} "
            f"matching images in {image_dir}."
        )

    rng = random.Random(seed)
    rng.shuffle(pairs)
    n_val = max(1, int(len(pairs) * val_split)) if len(pairs) > 1 else 0
    splits = {"val": pairs[:n_val], "train": pairs[n_val:]}

    if output_dir.exists():
        shutil.rmtree(output_dir)
    for split in splits:
        (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    counts = {}
    for split, items in splits.items():
        for img, lbl, _ in items:
            shutil.copy2(img, output_dir / "images" / split / img.name)
            shutil.copy2(lbl, output_dir / "labels" / split / f"{img.stem}.txt")
        counts[split] = len(items)

    data_yaml = output_dir / "data.yaml"
    data_yaml.write_text(
        f"path: {output_dir.resolve().as_posix()}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"nc: 1\n"
        f"names: [{POTHOLE_CLASS_NAME}]\n",
        encoding="utf-8",
    )

    return {
        "data_yaml": str(data_yaml),
        "train_images": counts.get("train", 0),
        "val_images": counts.get("val", 0),
        "with_boxes": sum(1 for _, _, hb in pairs if hb),
        "empty_negatives": sum(1 for _, _, hb in pairs if not hb),
        "skipped_unlabelled": skipped_unlabelled,
    }


def _auto_batch(device: str, imgsz: int, requested: Optional[int] = None) -> int:
    """Pick a batch size that fits the VRAM actually free right now.

    A 4GB laptop GPU shares memory with the desktop compositor and any running
    backend, so the safe batch depends on free memory at launch, not on card
    capacity. Ultralytics' own OOM retry cannot always recover here: when the
    card is nearly full its cache-clearing call fails too, taking down the run.
    """
    if device == "cpu":
        return requested or 4

    try:
        import torch

        torch.cuda.empty_cache()
        free_bytes, _ = torch.cuda.mem_get_info()
        free_gb = free_bytes / (1024 ** 3)
    except Exception:
        return requested or 4

    # Rough headroom per image at 640px for YOLOv8s, scaled by area.
    scale = (imgsz / 640.0) ** 2
    if free_gb >= 9.0:
        safe = 16
    elif free_gb >= 5.5:
        safe = 8
    elif free_gb >= 3.2:
        safe = 4
    elif free_gb >= 2.0:
        safe = 2
    else:
        safe = 1
    safe = max(1, int(safe / max(1.0, scale)))

    if requested is not None and requested <= safe:
        return requested

    if requested is not None:
        print(
            f"  note: {free_gb:.1f}GB VRAM free -> using batch={safe} "
            f"instead of {requested} to avoid CUDA OOM"
        )
    return safe


def _pick_detect_base() -> Path:
    """Choose a local detection-task checkpoint to start fine-tuning from.

    Not every bundled pothole model is a detector — keremberke_pothole_yolov8
    is a segmentation model and cannot be trained from box labels — so the
    task is checked rather than assumed from the filename.
    """
    from ultralytics import YOLO

    candidates = [
        MODELS_DIR / "pothole_yolov8.pt",
        MODELS_DIR / "keremberke_pothole_yolov8.pt",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            if getattr(YOLO(str(path)), "task", None) == "detect":
                return path
        except Exception:
            continue

    # Nothing local is usable; fall back to a stock COCO detector, which
    # Ultralytics fetches on first use.
    return Path("yolov8s.pt")


def finetune_yolo(
    data_yaml: Path | str,
    base_weights: Optional[Path | str] = None,
    epochs: int = 60,
    imgsz: int = 640,
    batch: Optional[int] = None,
    device: Optional[str] = None,
    project_dir: Optional[Path | str] = None,
    progress_callback: Optional[Callable[[int, float, int], None]] = None,
) -> Dict[str, Any]:
    """Fine-tune YOLOv8 and publish the best weights for inference.

    Args:
        data_yaml: Dataset descriptor from build_yolo_dataset.
        base_weights: Starting checkpoint. Defaults to the existing pretrained
            pothole model so training starts from pothole-aware features
            rather than from scratch on a small dataset.
        epochs: Training epochs.
        imgsz: Training image size.
        batch: Batch size, or None to size it from free VRAM.
        device: 'cuda', 'cpu', or None to auto-select.
        project_dir: Where Ultralytics writes run artefacts.
        progress_callback: Called as (epoch, loss, total_epochs) each epoch.

    Returns:
        Summary including the published weights path and validation metrics.
    """
    import os

    # Allocator fragmentation is what usually tips a small card over the edge;
    # expandable segments let PyTorch reuse partial blocks instead of failing.
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    from ultralytics import YOLO
    import torch

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    batch = _auto_batch(device, imgsz, batch)

    if base_weights is None:
        base_weights = _pick_detect_base()
    base_weights = Path(base_weights)
    if not base_weights.exists():
        raise FileNotFoundError(f"Base weights not found: {base_weights}")

    project_dir = Path(project_dir) if project_dir else (MODELS_DIR.parent / "runs")
    model = YOLO(str(base_weights))

    # Bounding-box labels cannot fine-tune a segmentation checkpoint: the
    # trainer demands one polygon per box and aborts. Fail early and clearly.
    if getattr(model, "task", "detect") != "detect":
        raise ValueError(
            f"{base_weights.name} is a '{model.task}' model, but training uses "
            f"bounding-box labels. Pass a detection checkpoint via base_weights."
        )

    if progress_callback is not None:
        def _on_epoch_end(trainer):
            epoch = int(getattr(trainer, "epoch", 0)) + 1
            loss = 0.0
            # tloss is the running per-component mean; loss is the last batch
            # total. Either may be a tensor, a scalar, or absent depending on
            # where in the epoch the callback fires.
            for attr in ("tloss", "loss"):
                raw = getattr(trainer, attr, None)
                if raw is None:
                    continue
                try:
                    value = raw.detach().sum().item() if hasattr(raw, "detach") else float(raw)
                except Exception:
                    continue
                if value:
                    loss = value
                    break
            progress_callback(epoch, loss, epochs)

        model.add_callback("on_train_epoch_end", _on_epoch_end)

    try:
        results = model.train(
            data=str(data_yaml),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=device,
            project=str(project_dir),
            name="pothole_finetune",
            exist_ok=True,
            patience=20,
            verbose=False,
            plots=False,
        )
    except Exception as exc:
        if "out of memory" not in str(exc).lower():
            raise
        raise RuntimeError(
            f"CUDA ran out of memory at batch={batch}, imgsz={imgsz}.\n"
            f"Free VRAM before training:\n"
            f"  - stop the backend server (it keeps YOLO weights resident on the GPU)\n"
            f"  - close GPU-heavy desktop apps (browsers, Copilot, chat clients)\n"
            f"Then retry, or lower the cost explicitly:\n"
            f"  python train_potholes.py train --batch 2 --imgsz 512"
        ) from exc

    save_dir = Path(getattr(results, "save_dir", project_dir / "pothole_finetune"))
    best = save_dir / "weights" / "best.pt"
    published = MODELS_DIR / FINETUNED_WEIGHTS_NAME
    if best.exists():
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best, published)

    metrics: Dict[str, float] = {}
    box = getattr(getattr(results, "box", None), "__dict__", {})
    for key in ("map", "map50"):
        val = getattr(getattr(results, "box", None), key, None)
        if val is not None:
            try:
                metrics[key] = float(val)
            except Exception:
                pass
    if not metrics and box:
        metrics = {k: float(v) for k, v in box.items() if isinstance(v, (int, float))}

    return {
        "weights_path": str(published if published.exists() else best),
        "run_dir": str(save_dir),
        "device": device,
        "epochs": epochs,
        "metrics": metrics,
    }
