import io
import time
import base64
from pathlib import Path
from typing import List, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from ultralytics import YOLO
from .config import settings
from .schemas import (
    DetectionBoxModel,
    DetectionResultResponse,
    CompanionImageResult,
    CompanionDetectionItem,
)

class PotholeDetector:
    def __init__(self, model_path: str = settings.MODEL_PATH):
        self.model_path = model_path
        self.model = None
        self.classes: List[str] = ["pothole"]
        self.load_model()

    def load_model(self):
        print(f"Loading YOLOv8 model from {self.model_path} onto CPU...")
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"Model file not found at {self.model_path}")
        self.model = YOLO(self.model_path)
        if hasattr(self.model, "names") and isinstance(self.model.names, dict):
            self.classes = list(self.model.names.values())
        print(f"Model loaded successfully. Classes: {self.classes}")

    def _image_to_base64(self, img: Image.Image, format: str = "JPEG") -> str:
        buffered = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(buffered, format=format, quality=88)
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/{format.lower()};base64,{encoded}"

    def _calculate_severity(self, area_pct: float) -> Tuple[str, float, str]:
        """
        Severity bands by share of frame covered by the box:
        - under 1 percent is Low (score 1.5, #16a34a / green)
        - 1 to 4 percent is Moderate (score 3.0, #f59e0b / amber)
        - over 4 percent is Severe (score 5.0, #ef4444 / red)
        """
        if area_pct < 1.0:
            return "Low", 1.5, "#16a34a"
        elif area_pct <= 4.0:
            return "Moderate", 3.0, "#f59e0b"
        else:
            return "Severe", 5.0, "#ef4444"

    def _draw_detections(
        self,
        image: Image.Image,
        detections: List[Dict[str, Any]]
    ) -> Image.Image:
        annotated = image.copy().convert("RGBA")
        overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        FONT_CANDIDATES = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "arial.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
        font_size = max(14, int(min(image.size) * 0.025))
        font = None
        for font_path in FONT_CANDIDATES:
            try:
                font = ImageFont.truetype(font_path, size=font_size)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        for d in detections:
            box = d["box"]
            color_hex = d["color"]
            code = d["code"]
            conf = d["confidence"]
            severity = d["severity"]
            
            # Parse hex to RGB
            hex_clean = color_hex.lstrip("#")
            r, g, b = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
            
            x1, y1, x2, y2 = box
            
            # Semi-transparent box fill
            draw.rectangle([x1, y1, x2, y2], fill=(r, g, b, 45), outline=(r, g, b, 230), width=3)
            
            # Label banner
            label_text = f"#{d['index']} {code} {d['name']} {conf}% [{severity}]"
            
            # Calculate text bounding box
            text_bbox = draw.textbbox((x1, y1), label_text, font=font)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
            
            banner_y1 = max(0, y1 - text_h - 8)
            banner_y2 = max(text_h + 8, y1)
            banner_x2 = min(image.width, x1 + text_w + 12)
            
            draw.rectangle([x1, banner_y1, banner_x2, banner_y2], fill=(r, g, b, 240))
            draw.text((x1 + 6, banner_y1 + 4), label_text, fill=(255, 255, 255, 255), font=font)

        annotated = Image.alpha_composite(annotated, overlay)
        return annotated.convert("RGB")

    def detect(
        self,
        image: Image.Image,
        filename: str = "image.jpg",
        conf: float = settings.DEFAULT_CONF,
        iou: float = settings.DEFAULT_IOU,
        imgsz: int = settings.DEFAULT_IMGSZ,
    ) -> DetectionResultResponse:
        start_time = time.perf_counter()

        if image.mode != "RGB":
            image = image.convert("RGB")

        orig_w, orig_h = image.size
        frame_area = max(1.0, float(orig_w * orig_h))

        # Run inference on CPU
        results = self.model.predict(
            source=image,
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            device="cpu",
            verbose=False,
        )

        r = results[0]
        boxes_out: List[DetectionBoxModel] = []
        raw_detections: List[Dict[str, Any]] = []
        companion_detections: List[CompanionDetectionItem] = []

        total_severity_score = 0.0

        if r.boxes is not None and len(r.boxes) > 0:
            for idx, box in enumerate(r.boxes, start=1):
                xyxy = [round(float(v), 1) for v in box.xyxy[0].tolist()]
                x1, y1, x2, y2 = xyxy
                box_w = max(0.0, x2 - x1)
                box_h = max(0.0, y2 - y1)
                box_area = round(box_w * box_h, 1)
                area_pct = round((box_area / frame_area) * 100.0, 2)

                cls_idx = int(box.cls[0])
                cls_name = self.model.names.get(cls_idx, "pothole")
                raw_conf = float(box.conf[0])
                conf_pct = round(raw_conf * 100.0, 1)

                severity, sev_score, color = self._calculate_severity(area_pct)
                total_severity_score += sev_score

                # Map class to JRA damage code
                code = "D40" if "pothole" in cls_name.lower() else "D00"
                category = "Pothole / Rutting" if code == "D40" else "Pavement Defect"

                box_item = DetectionBoxModel(
                    index=idx,
                    code=code,
                    name="Pothole" if code == "D40" else cls_name.title(),
                    category=category,
                    severity=severity,
                    severity_score=sev_score,
                    color=color,
                    confidence=conf_pct,
                    box=xyxy,
                    area=box_area,
                )
                boxes_out.append(box_item)

                raw_detections.append({
                    "index": idx,
                    "code": code,
                    "name": box_item.name,
                    "severity": severity,
                    "color": color,
                    "confidence": conf_pct,
                    "box": xyxy,
                })

                companion_detections.append(
                    CompanionDetectionItem(
                        class_name=cls_name,
                        confidence=round(raw_conf, 3),
                        bbox=xyxy,
                        area_pct=area_pct,
                        severity=severity,
                    )
                )

        # Draw annotations
        annotated_img = self._draw_detections(image, raw_detections)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 1)
        total_defects = len(boxes_out)
        avg_sev_score = round(total_severity_score / max(1, total_defects), 1) if total_defects > 0 else 0.0

        # Custom composite damage score (0 to 100, where 100 is pristine)
        composite_score = max(15.0, round(100.0 - (total_defects * 12.0) - (avg_sev_score * 3.5), 1))

        annotated_b64 = self._image_to_base64(annotated_img)
        original_b64 = self._image_to_base64(image)

        companion_results = [
            CompanionImageResult(
                filename=filename,
                detections=companion_detections,
                annotated_image=annotated_b64,
            )
        ]

        return DetectionResultResponse(
            success=True,
            inference_time_ms=elapsed_ms,
            total_defects=total_defects,
            severity_score=avg_sev_score,
            composite_damage_score=composite_score,
            boxes=boxes_out,
            annotated_image=annotated_b64,
            original_image=original_b64,
            road_mask="",
            results=companion_results,
        )

# Global singleton detector instance
detector_instance = PotholeDetector()
