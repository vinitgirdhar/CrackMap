"""
Evaluation metrics for Road Damage Detection.
Computes IoU, Precision, Recall, F1-score, and mean Average Precision (mAP@0.5).
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
from collections import defaultdict
import torch

from src.config import CLASS_NAMES
from src.dataset.voc_parser import parse_voc_dataset_dir, BoundingBox
from src.models.inference import RoadDamageInferenceEngine


def compute_iou(box1: List[float] | Tuple[float, ...], box2: List[float] | Tuple[float, ...]) -> float:
    """Compute Intersection over Union (IoU) between two bounding boxes [xmin, ymin, xmax, ymax]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if intersection <= 0.0:
        return 0.0

    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection

    return intersection / max(1e-6, union)


def calculate_map(
    ground_truths: Dict[str, List[BoundingBox]],
    predictions: Dict[str, List[BoundingBox]],
    iou_threshold: float = 0.5
) -> Dict[str, Any]:
    """Calculate Precision, Recall, AP per class and mAP@0.5."""
    class_metrics = {}
    aps = []

    for cls_name in CLASS_NAMES:
        cls_gts = {img_id: [b for b in boxes if b.name == cls_name] for img_id, boxes in ground_truths.items()}
        total_gt = sum(len(b) for b in cls_gts.values())

        # Collect all predictions for this class
        all_preds = []
        for img_id, boxes in predictions.items():
            for b in boxes:
                if b.name == cls_name:
                    all_preds.append((img_id, b.confidence or 0.0, [b.xmin, b.ymin, b.xmax, b.ymax]))

        if total_gt == 0 and len(all_preds) == 0:
            continue

        if total_gt == 0 and len(all_preds) > 0:
            class_metrics[cls_name] = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "ap": 0.0, "support": 0}
            aps.append(0.0)
            continue

        if len(all_preds) == 0:
            class_metrics[cls_name] = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "ap": 0.0, "support": total_gt}
            aps.append(0.0)
            continue

        # Sort predictions by descending confidence
        all_preds.sort(key=lambda x: x[1], reverse=True)

        tp = np.zeros(len(all_preds))
        fp = np.zeros(len(all_preds))
        matched_gt = defaultdict(set)

        for i, (img_id, conf, pred_box) in enumerate(all_preds):
            gt_boxes = cls_gts.get(img_id, [])
            best_iou = 0.0
            best_gt_idx = -1

            for gt_idx, gt_b in enumerate(gt_boxes):
                if gt_idx in matched_gt[img_id]:
                    continue
                iou = compute_iou(pred_box, [gt_b.xmin, gt_b.ymin, gt_b.xmax, gt_b.ymax])
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = gt_idx

            if best_iou >= iou_threshold and best_gt_idx != -1:
                tp[i] = 1.0
                matched_gt[img_id].add(best_gt_idx)
            else:
                fp[i] = 1.0

        # Cumulative precision and recall
        cum_tp = np.cumsum(tp)
        cum_fp = np.cumsum(fp)
        recalls = cum_tp / max(1, total_gt)
        precisions = cum_tp / np.maximum(cum_tp + cum_fp, 1e-6)

        # 11-point interpolated AP
        ap = 0.0
        for t in np.arange(0.0, 1.1, 0.1):
            p = np.max(precisions[recalls >= t]) if np.sum(recalls >= t) > 0 else 0.0
            ap += p / 11.0

        final_precision = float(precisions[-1]) if len(precisions) > 0 else 0.0
        final_recall = float(recalls[-1]) if len(recalls) > 0 else 0.0
        f1 = (2 * final_precision * final_recall) / max(1e-6, final_precision + final_recall)

        class_metrics[cls_name] = {
            "precision": round(final_precision, 4),
            "recall": round(final_recall, 4),
            "f1": round(f1, 4),
            "ap": round(float(ap), 4),
            "support": total_gt
        }
        aps.append(float(ap))

    mean_ap = float(np.mean(aps)) if aps else 0.0

    return {
        "mAP_50": round(mean_ap, 4),
        "class_metrics": class_metrics,
        "num_evaluated_classes": len(aps)
    }


def evaluate_detector(
    dataset_dir: Path | str,
    inference_engine: RoadDamageInferenceEngine,
    confidence_threshold: float = 0.35,
    iou_threshold: float = 0.5
) -> Dict[str, Any]:
    """Run full evaluation on a test dataset directory."""
    parsed = parse_voc_dataset_dir(dataset_dir)
    ground_truths: Dict[str, List[BoundingBox]] = {}
    predictions: Dict[str, List[BoundingBox]] = {}

    for ann in parsed["annotations"]:
        ground_truths[ann.filename] = ann.boxes
        
        # Locate corresponding image
        img_path = Path(dataset_dir) / "JPEGImages" / ann.filename
        if not img_path.exists():
            img_path = ann.filepath.parent.parent / "JPEGImages" / ann.filename
        
        if img_path.exists():
            res = inference_engine.predict(img_path, custom_conf_threshold=confidence_threshold)
            predictions[ann.filename] = res.boxes
        else:
            predictions[ann.filename] = []

    metrics = calculate_map(ground_truths, predictions, iou_threshold=iou_threshold)
    metrics["total_images"] = parsed["total_images"]
    metrics["total_ground_truth_boxes"] = parsed["total_boxes"]
    return metrics
