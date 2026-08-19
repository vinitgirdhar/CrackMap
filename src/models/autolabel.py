"""Pseudo-label generation for pothole training data.

Produces YOLO-format label files from the pretrained detectors so a human can
review them instead of drawing every box from scratch. Detection runs at a
deliberately LOW confidence so the output over-proposes: deleting a wrong box
in a review tool is far quicker than finding and drawing a missed one.
"""

from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from PIL import Image

from src.models.advanced_detector import AdvancedRoadDamageDetector

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Single-class pothole detector: the source images are pothole photos and both
# pretrained backbones are pothole models, so a one-class problem is what the
# data can actually support. Crack classes still come from the classical pass.
POTHOLE_CLASS_ID = 0
POTHOLE_CLASS_NAME = "pothole"


def _to_yolo_line(box, img_w: int, img_h: int) -> Optional[str]:
    """Convert a pixel-space box to a normalised YOLO label line."""
    x1 = max(0, min(box.xmin, img_w - 1))
    y1 = max(0, min(box.ymin, img_h - 1))
    x2 = max(0, min(box.xmax, img_w - 1))
    y2 = max(0, min(box.ymax, img_h - 1))

    bw = x2 - x1
    bh = y2 - y1
    if bw <= 1 or bh <= 1:
        return None

    xc = (x1 + x2) / 2.0 / img_w
    yc = (y1 + y2) / 2.0 / img_h
    return f"{POTHOLE_CLASS_ID} {xc:.6f} {yc:.6f} {bw / img_w:.6f} {bh / img_h:.6f}"


def generate_pseudo_labels(
    image_dir: Path | str,
    label_dir: Path | str,
    conf_threshold: float = 0.12,
    detector: Optional[AdvancedRoadDamageDetector] = None,
    overwrite: bool = False,
) -> Dict[str, int]:
    """Write one YOLO .txt label file per image for human review.

    Args:
        image_dir: Directory of source images.
        label_dir: Destination for .txt label files (same stem as the image).
        conf_threshold: Low on purpose so the pass over-proposes boxes.
        detector: Reuse an existing detector instance if provided.
        overwrite: Re-label images that already have a label file. Off by
            default so a review pass is never silently destroyed.

    Returns:
        Summary counts: images processed, labelled, skipped, and total boxes.
    """
    image_dir = Path(image_dir)
    label_dir = Path(label_dir)
    label_dir.mkdir(parents=True, exist_ok=True)

    if detector is None:
        detector = AdvancedRoadDamageDetector()

    images = sorted(p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    stats = {"images": len(images), "labelled": 0, "skipped": 0, "boxes": 0, "empty": 0}

    for img_path in images:
        out_path = label_dir / f"{img_path.stem}.txt"
        if out_path.exists() and not overwrite:
            stats["skipped"] += 1
            continue

        try:
            img_np = np.array(Image.open(img_path).convert("RGB"))
        except Exception as exc:  # unreadable/corrupt file
            print(f"  skip {img_path.name}: {exc}")
            stats["skipped"] += 1
            continue

        h, w = img_np.shape[:2]
        road_mask = detector.extract_road_corridor_mask(img_np)

        # Neural detections only. The classical pass is tuned for precision on
        # display, not recall, and its crack guesses would pollute the labels.
        lines: List[str] = []
        for model in detector.yolo_models:
            try:
                results = model.predict(
                    source=img_np, conf=conf_threshold, device=detector.device, verbose=False
                )
            except Exception as exc:
                print(f"  inference issue on {img_path.name}: {exc}")
                continue
            if not results:
                continue
            for raw in results[0].boxes:
                xyxy = raw.xyxy[0].cpu().numpy().astype(int)
                cx, cy = (xyxy[0] + xyxy[2]) // 2, (xyxy[1] + xyxy[3]) // 2
                if 0 <= cy < h and 0 <= cx < w and road_mask[cy, cx] == 0:
                    continue
                from src.dataset.voc_parser import BoundingBox
                box = BoundingBox(
                    name="D40",
                    xmin=int(xyxy[0]), ymin=int(xyxy[1]),
                    xmax=int(xyxy[2]), ymax=int(xyxy[3]),
                    confidence=float(raw.conf[0].cpu().numpy()),
                )
                line = _to_yolo_line(box, w, h)
                if line:
                    lines.append(line)

        # Merge near-duplicates the two backbones both proposed.
        deduped = _dedupe_lines(lines)
        out_path.write_text("\n".join(deduped) + ("\n" if deduped else ""), encoding="utf-8")

        stats["labelled"] += 1
        stats["boxes"] += len(deduped)
        if not deduped:
            stats["empty"] += 1

    return stats


def _dedupe_lines(lines: List[str], iou_thresh: float = 0.55) -> List[str]:
    """Drop near-identical normalised boxes produced by both backbones."""
    parsed = []
    for ln in lines:
        parts = ln.split()
        xc, yc, bw, bh = (float(v) for v in parts[1:5])
        parsed.append((xc - bw / 2, yc - bh / 2, xc + bw / 2, yc + bh / 2, ln))

    keep: List[tuple] = []
    for cand in parsed:
        duplicate = False
        for kept in keep:
            ix = max(0.0, min(cand[2], kept[2]) - max(cand[0], kept[0]))
            iy = max(0.0, min(cand[3], kept[3]) - max(cand[1], kept[1]))
            inter = ix * iy
            a1 = (cand[2] - cand[0]) * (cand[3] - cand[1])
            a2 = (kept[2] - kept[0]) * (kept[3] - kept[1])
            if inter / max(1e-9, a1 + a2 - inter) > iou_thresh:
                duplicate = True
                break
        if not duplicate:
            keep.append(cand)

    return [k[4] for k in keep]
