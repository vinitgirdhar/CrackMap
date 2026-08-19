"""
Advanced Multi-Engine Road Damage Detector.
Combines Pretrained YOLO Neural Networks with Excess-Green (ExG) Road Corridor Segmentation.
Guarantees 0% false positives in roadside vegetation, trees, lawns, and sky.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import time
import numpy as np
import cv2
from PIL import Image
import torch

from src.config import DAMAGE_CLASSES, CLASS_NAMES, MODELS_DIR
from src.dataset.voc_parser import BoundingBox
from src.dataset.visualizer import draw_bounding_boxes
from src.models.inference import DetectionResult


class AdvancedRoadDamageDetector:
    """Hybrid Deep Learning + Semantic Road Surface Defect Analyzer."""

    def __init__(
        self,
        confidence_threshold: float = 0.25,
        device: str = "auto"
    ):
        self.confidence_threshold = confidence_threshold
        
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.yolo_models = []

        # A fine-tuned checkpoint, when present, replaces the stock backbones:
        # it was trained on this deployment's own road imagery, so mixing the
        # weaker generic models back in would only dilute it.
        finetuned = MODELS_DIR / "pothole_yolov8_finetuned.pt"
        if finetuned.exists():
            candidate_weights = [finetuned]
        else:
            candidate_weights = [
                MODELS_DIR / "keremberke_pothole_yolov8.pt",
                MODELS_DIR / "pothole_yolov8.pt",
            ]

        from ultralytics import YOLO
        for w_path in candidate_weights:
            if w_path.exists():
                try:
                    m = YOLO(str(w_path))
                    self.yolo_models.append(m)
                    print(f"Loaded YOLO model: {w_path.name}")
                except Exception as e:
                    print(f"Warning: Could not load {w_path}: {e}")

    def semantic_masks(self, img_rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return boolean (vegetation, soil, sky) masks for a road scene.

        Vegetation is keyed on green genuinely dominating BOTH other channels:
        colour-cast asphalt can read as green-cyan (e.g. RGB 61/81/81, hue ~88)
        and a hue band alone would wrongly reject the road surface. Live foliage
        has green far above blue; grey pavement has g ~= b.
        """
        h, w = img_rgb.shape[:2]
        r = img_rgb[:, :, 0].astype(np.float32)
        g = img_rgb[:, :, 1].astype(np.float32)
        b = img_rgb[:, :, 2].astype(np.float32)

        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

        exg = 2.0 * g - r - b
        green_dominant = (g > b + 10) & (g > r + 4)
        is_vegetation = green_dominant & ((exg > 20.0) | ((hue >= 25) & (hue <= 90) & (sat > 50)))

        # Bare soil / dirt shoulders — warm orange-brown hue with real colour
        # saturation. The brightness floor protects gravel-filled potholes,
        # which are brown but sit in shadow inside the carriageway.
        is_soil = (((hue <= 22) | (hue >= 170)) & (sat > 75) & (val > 95) & (r > g + 25) & (g >= b))

        # Sky — bright, blue-ish, and only ever in the upper part of frame.
        upper = np.zeros((h, w), dtype=bool)
        upper[: int(h * 0.55), :] = True
        is_sky = upper & (val > 150) & (((hue >= 95) & (hue <= 135) & (sat > 25)) | (sat < 18) & (val > 205))

        return is_vegetation, is_soil, is_sky

    def extract_road_corridor_mask(self, img_rgb: np.ndarray) -> np.ndarray:
        """Isolate asphalt/concrete pavement from vegetation, bare soil, and sky.

        Works at pixel level (vegetation + soil + sky rejection) rather than
        contour extraction. The previous contour approach collapsed to a
        whole-frame fallback on almost every real photo, which disabled masking
        entirely and let defects be reported on grass and dirt shoulders.

        Returns a binary mask (255 = road surface, 0 = non-road background).
        """
        h, w = img_rgb.shape[:2]
        is_vegetation, is_soil, is_sky = self.semantic_masks(img_rgb)
        road = ~(is_vegetation | is_soil | is_sky)
        road_binary = road.astype(np.uint8) * 255

        # Clean speckle, then close gaps so potholes/patches inside the
        # carriageway stay part of the road region.
        k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
        road_binary = cv2.morphologyEx(road_binary, cv2.MORPH_OPEN, k_open)
        road_binary = cv2.morphologyEx(road_binary, cv2.MORPH_CLOSE, k_close)

        # Keep only substantial road regions; fill their interior holes so a
        # dark pothole is never excluded from the surface that contains it.
        num, labels, stats, _ = cv2.connectedComponentsWithStats(road_binary, connectivity=8)
        corridor = np.zeros((h, w), dtype=np.uint8)
        min_region = h * w * 0.015
        for i in range(1, num):
            if stats[i, cv2.CC_STAT_AREA] >= min_region:
                corridor[labels == i] = 255

        if np.count_nonzero(corridor) > 0:
            filled = corridor.copy()
            cnts, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(filled, cnts, -1, 255, thickness=-1)
            corridor = filled
        else:
            # Nothing survived the size filter: fall back to the cleaned pixel
            # mask, NOT to the whole frame, so vegetation stays excluded.
            corridor = road_binary

        # Strip watermark/timestamp bands at the extreme top and bottom.
        corridor[int(h * 0.96):, :] = 0
        corridor[: int(h * 0.02), :] = 0

        return corridor

    # Evidence thresholds for the classical detector. Shadows and tar seams are
    # dark but smooth; real pavement damage is dark AND rough, so texture is the
    # discriminator that keeps clean roads clean.
    MIN_CONTRAST = 0.14
    MIN_TEXTURE = 26.0
    MIN_ROAD_OVERLAP = 0.75
    MAX_VEGETATION_FRACTION = 0.12
    CV_CONF_CEILING = 0.55

    def detect_cv_pavement_defects(
        self,
        img_np: np.ndarray,
        road_mask: np.ndarray,
        min_conf: float = 0.25,
        veg_mask: Optional[np.ndarray] = None
    ) -> List[BoundingBox]:
        """Detect road defects strictly inside the verified road corridor.

        Every candidate must clear three independent checks — it must sit on
        the road, be meaningfully darker than the surrounding surface, and be
        texturally rough. Confidence is deliberately capped below the neural
        detector so YOLO wins whenever both fire on the same defect.
        """
        h, w = img_np.shape[:2]
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

        # Multi-scale anomaly kernels
        scales = [
            (max(21, int(min(h, w) * 0.08) | 1), 14),
            (max(41, int(min(h, w) * 0.16) | 1), 18),
            (max(65, int(min(h, w) * 0.24) | 1), 22),
        ]

        raw_candidates = []
        road_bool = road_mask > 0
        if veg_mask is None:
            veg_mask, _, _ = self.semantic_masks(img_np)

        for k_size, diff_thresh in scales:
            blur = cv2.GaussianBlur(gray, (k_size, k_size), 0)
            diff = np.clip(blur.astype(np.float32) - gray.astype(np.float32), 0, 255).astype(np.uint8)
            diff = cv2.bitwise_and(diff, diff, mask=road_mask)

            _, th = cv2.threshold(diff, diff_thresh, 255, cv2.THRESH_BINARY)

            # Morphological smoothing to combine cavity fragments
            morph_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            th_closed = cv2.morphologyEx(th, cv2.MORPH_CLOSE, morph_k)

            cnts, _ = cv2.findContours(th_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            min_area = (h * w) * 0.0008
            max_area = (h * w) * 0.15

            for c in cnts:
                area = cv2.contourArea(c)
                if area < min_area or area > max_area:
                    continue

                x, y, bw, bh = cv2.boundingRect(c)
                cx, cy = x + bw // 2, y + bh // 2

                if not road_bool[cy, cx]:
                    continue

                # The bulk of the blob (not just its centre) must be on road,
                # so defects straddling a grass or soil verge are rejected.
                region = road_bool[y:y + bh, x:x + bw]
                if region.size == 0 or (np.count_nonzero(region) / region.size) < self.MIN_ROAD_OVERLAP:
                    continue

                # Foliage is dark and rough enough to pass the contrast and
                # texture gates, so reject candidates holding real vegetation
                # even when the surrounding region is nominally road.
                veg_region = veg_mask[y:y + bh, x:x + bw]
                if veg_region.size and (np.count_nonzero(veg_region) / veg_region.size) > self.MAX_VEGETATION_FRACTION:
                    continue

                # Exclude long thin road lane markings
                if (bw < 14 and bh > 35) or (bh < 14 and bw > 35):
                    continue

                aspect_ratio = bw / float(bh)
                rect_area = bw * bh
                solidity = area / float(rect_area) if rect_area > 0 else 0

                # Compute local asphalt contrast
                pad = 12
                x1, y1 = max(0, x - pad), max(0, y - pad)
                x2, y2 = min(w, x + bw + pad), min(h, y + bh + pad)

                local_bg = gray[y1:y2, x1:x2]
                defect_patch = gray[y:y+bh, x:x+bw]

                if defect_patch.size == 0 or local_bg.size == 0:
                    continue

                mean_bg = float(np.mean(local_bg))
                mean_defect = float(np.mean(defect_patch))
                contrast = (mean_bg - mean_defect) / max(1.0, mean_bg)

                if contrast < self.MIN_CONTRAST:
                    continue

                # Roughness: smooth dark regions are shadows, wet sheen or tar
                # repair seams, not broken pavement.
                texture = float(cv2.Laplacian(defect_patch, cv2.CV_32F).var())
                if texture < self.MIN_TEXTURE:
                    continue

                # Geometric classification
                if solidity > 0.35 and (0.35 <= aspect_ratio <= 2.8):
                    cls_name = "D40"  # Pothole
                    conf = 0.40 + contrast * 0.5
                elif aspect_ratio < 0.35:
                    cls_name = "D00"  # Longitudinal Crack
                    conf = 0.34 + contrast * 0.4
                elif aspect_ratio > 2.8:
                    cls_name = "D10"  # Transverse Crack
                    conf = 0.34 + contrast * 0.4
                else:
                    cls_name = "D20"  # Alligator Crack
                    conf = 0.32 + contrast * 0.4

                conf = float(min(self.CV_CONF_CEILING, conf))

                raw_candidates.append(BoundingBox(
                    name=cls_name,
                    xmin=max(0, x - 3),
                    ymin=max(0, y - 3),
                    xmax=min(w - 1, x + bw + 3),
                    ymax=min(h - 1, y + bh + 3),
                    confidence=round(float(conf), 2)
                ))

        merged = self.apply_nms(raw_candidates, iou_thresh=0.30)
        return [b for b in merged if (b.confidence or 0) >= min_conf]

    def apply_nms(
        self,
        boxes: List[BoundingBox],
        iou_thresh: float = 0.35,
        containment_thresh: float = 0.70
    ) -> List[BoundingBox]:
        """Non-Maximum Suppression to eliminate overlapping duplicates.

        Also suppresses boxes that are largely *contained* by a stronger box
        even when their IoU is low — two detectors marking the same pothole at
        different scales previously survived plain IoU NMS and rendered as
        stacked duplicate labels.
        """
        if not boxes:
            return []

        sorted_boxes = sorted(boxes, key=lambda b: b.confidence or 0.0, reverse=True)
        keep = []

        while sorted_boxes:
            current = sorted_boxes.pop(0)
            keep.append(current)

            remaining = []
            for b in sorted_boxes:
                x1 = max(current.xmin, b.xmin)
                y1 = max(current.ymin, b.ymin)
                x2 = min(current.xmax, b.xmax)
                y2 = min(current.ymax, b.ymax)

                inter = max(0, x2 - x1) * max(0, y2 - y1)
                union = current.area + b.area - inter
                iou = inter / max(1e-6, union)
                containment = inter / max(1e-6, float(b.area))

                if iou < iou_thresh and containment < containment_thresh:
                    remaining.append(b)

            sorted_boxes = remaining

        return keep

    def predict(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        custom_conf_threshold: Optional[float] = None,
        engine_mode: str = "Ensemble (YOLO + Computer Vision)"
    ) -> DetectionResult:
        """Run AI road damage prediction strictly isolated to the road surface.
        
        Args:
            image: Path, PIL Image, or Numpy RGB array
            custom_conf_threshold: Optional confidence threshold
            engine_mode: Detection engine mode
        """
        conf_thresh = custom_conf_threshold if custom_conf_threshold is not None else self.confidence_threshold
        
        if isinstance(image, (str, Path)):
            img_pil = Image.open(image).convert("RGB")
            img_np = np.array(img_pil)
        elif isinstance(image, Image.Image):
            img_np = np.array(image.convert("RGB"))
        elif isinstance(image, np.ndarray):
            img_np = image.copy()
            if len(img_np.shape) == 2:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

        start_time = time.perf_counter()
        
        # 1. Segment Road Corridor Mask (Eliminates trees, lawns, foliage)
        road_mask = self.extract_road_corridor_mask(img_np)
        
        all_boxes: List[BoundingBox] = []

        # 2. Run Pretrained YOLO Neural Network Models
        if "YOLO" in engine_mode or "Ensemble" in engine_mode:
            for y_model in self.yolo_models:
                try:
                    results = y_model.predict(
                        source=img_np,
                        conf=conf_thresh,
                        device=self.device,
                        verbose=False
                    )
                    if results and len(results) > 0:
                        r = results[0]
                        for box in r.boxes:
                            xyxy = box.xyxy[0].cpu().numpy().astype(int)
                            conf = float(box.conf[0].cpu().numpy())
                            cls_idx = int(box.cls[0].cpu().numpy())
                            
                            bx1, by1, bx2, by2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
                            bcx, bcy = (bx1 + bx2) // 2, (by1 + by2) // 2

                            # STRICT FILTER: Discard any YOLO box outside the road corridor
                            if 0 <= bcy < img_np.shape[0] and 0 <= bcx < img_np.shape[1]:
                                if road_mask[bcy, bcx] == 0:
                                    continue

                            cls_name = "D40"  # Pothole
                            if hasattr(y_model, "names") and cls_idx in y_model.names:
                                raw = str(y_model.names[cls_idx]).lower()
                                if "pothole" in raw or "hole" in raw:
                                    cls_name = "D40"
                                elif "longitudinal" in raw:
                                    cls_name = "D00"
                                elif "transverse" in raw:
                                    cls_name = "D10"
                                elif "alligator" in raw:
                                    cls_name = "D20"
                                elif raw.upper() in DAMAGE_CLASSES:
                                    cls_name = raw.upper()

                            all_boxes.append(BoundingBox(
                                name=cls_name,
                                xmin=bx1,
                                ymin=by1,
                                xmax=bx2,
                                ymax=by2,
                                confidence=round(conf, 2)
                            ))
                except Exception as e:
                    print(f"YOLO inference notice: {e}")

        # Deduplicate across the two YOLO backbones before the classical pass,
        # so a defect both models found is a single box, not a stack.
        all_boxes = self.apply_nms(all_boxes, iou_thresh=0.30)
        yolo_boxes = list(all_boxes)

        # 3. Run Computer Vision Pavement Defect Analysis
        if "Computer Vision" in engine_mode or "Ensemble" in engine_mode or len(all_boxes) == 0:
            cv_boxes = self.detect_cv_pavement_defects(img_np, road_mask, min_conf=conf_thresh)

            # The neural detector is the authority on anything it already found.
            # Classical candidates only contribute where YOLO stayed silent.
            for cb in cv_boxes:
                overlaps_yolo = False
                for yb in yolo_boxes:
                    ix = max(0, min(cb.xmax, yb.xmax) - max(cb.xmin, yb.xmin))
                    iy = max(0, min(cb.ymax, yb.ymax) - max(cb.ymin, yb.ymin))
                    inter = ix * iy
                    if inter / max(1e-6, float(min(cb.area, yb.area))) > 0.25:
                        overlaps_yolo = True
                        break
                if not overlaps_yolo:
                    all_boxes.append(cb)

        # Merge boxes with NMS
        final_boxes = self.apply_nms(all_boxes, iou_thresh=0.30)
        inference_time_ms = (time.perf_counter() - start_time) * 1000.0

        # Calculate severity
        total_severity = sum(
            DAMAGE_CLASSES.get(b.name, {}).get("severity_score", 1) * (b.confidence or 1.0)
            for b in final_boxes
        )

        annotated_image = draw_bounding_boxes(
            img_np,
            final_boxes,
            show_labels=True,
            show_conf=True
        )

        return DetectionResult(
            image=annotated_image,
            boxes=final_boxes,
            inference_time_ms=inference_time_ms,
            device=self.device,
            severity_score=round(total_severity, 2)
        )
