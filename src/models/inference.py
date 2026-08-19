"""
Inference engine for Road Damage Detection.
Supports single image inference, batch inference, video streams, and NMS post-processing.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import time
import numpy as np
from PIL import Image
import torch
import cv2

from src.config import CLASS_NAMES, DAMAGE_CLASSES
from src.dataset.voc_parser import BoundingBox
from src.dataset.visualizer import draw_bounding_boxes
from src.models.detector import build_road_damage_detector, RoadDamageDetectorNet


@dataclass
class DetectionResult:
    image: np.ndarray
    boxes: List[BoundingBox]
    inference_time_ms: float
    device: str
    severity_score: float

    @property
    def num_detections(self) -> int:
        return len(self.boxes)

    @property
    def class_counts(self) -> Dict[str, int]:
        counts = {}
        for b in self.boxes:
            counts[b.name] = counts.get(b.name, 0) + 1
        return counts


class RoadDamageInferenceEngine:
    """High performance inference pipeline for road damage models."""

    def __init__(
        self,
        model: Optional[RoadDamageDetectorNet] = None,
        architecture: str = "fasterrcnn_mobilenet",
        checkpoint_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        device: Optional[str] = None
    ):
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        if model is not None:
            self.model = model.to(self.device)
        else:
            self.model = build_road_damage_detector(
                architecture=architecture,
                checkpoint_path=checkpoint_path,
                device=self.device
            )

        self.model.eval()

    def preprocess_image(self, image: Union[str, Path, np.ndarray, Image.Image]) -> Tuple[torch.Tensor, np.ndarray]:
        """Convert input to normalized PyTorch tensor [C, H, W] and RGB numpy array."""
        if isinstance(image, (str, Path)):
            img_pil = Image.open(image).convert("RGB")
            img_np = np.array(img_pil)
        elif isinstance(image, Image.Image):
            img_pil = image.convert("RGB")
            img_np = np.array(img_pil)
        elif isinstance(image, np.ndarray):
            if len(image.shape) == 2:
                img_np = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                img_np = image.copy()
        else:
            raise ValueError(f"Unsupported image input type: {type(image)}")

        # Convert to tensor [3, H, W], float range [0, 1]
        tensor = torch.from_numpy(img_np.transpose((2, 0, 1))).float() / 255.0
        return tensor.to(self.device), img_np

    @torch.no_grad()
    def predict(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        custom_conf_threshold: Optional[float] = None
    ) -> DetectionResult:
        """Run road damage detection on an image.
        
        Args:
            image: Image path, PIL Image, or Numpy RGB array
            custom_conf_threshold: Optional confidence threshold override
            
        Returns:
            DetectionResult with bounding boxes, runtime, and damage metrics
        """
        conf_thresh = custom_conf_threshold if custom_conf_threshold is not None else self.confidence_threshold
        tensor, original_np = self.preprocess_image(image)

        start_time = time.perf_counter()
        predictions = self.model([tensor])
        inference_time_ms = (time.perf_counter() - start_time) * 1000.0

        pred = predictions[0]
        boxes_raw = pred["boxes"].detach().cpu().numpy()
        scores_raw = pred["scores"].detach().cpu().numpy()
        labels_raw = pred["labels"].detach().cpu().numpy()

        detected_boxes: List[BoundingBox] = []
        total_severity = 0.0

        for box, score, label_id in zip(boxes_raw, scores_raw, labels_raw):
            if score < conf_thresh:
                continue

            # Class index 0 is background; 1..8 correspond to CLASS_NAMES
            if 1 <= label_id <= len(CLASS_NAMES):
                cls_name = CLASS_NAMES[label_id - 1]
                b = BoundingBox(
                    name=cls_name,
                    xmin=int(box[0]),
                    ymin=int(box[1]),
                    xmax=int(box[2]),
                    ymax=int(box[3]),
                    confidence=float(score)
                )
                if b.is_valid:
                    detected_boxes.append(b)
                    severity = DAMAGE_CLASSES.get(cls_name, {}).get("severity_score", 1)
                    total_severity += severity * float(score)

        # Draw annotations on image
        annotated_image = draw_bounding_boxes(
            original_np,
            detected_boxes,
            show_labels=True,
            show_conf=True
        )

        return DetectionResult(
            image=annotated_image,
            boxes=detected_boxes,
            inference_time_ms=inference_time_ms,
            device=self.device,
            severity_score=round(total_severity, 2)
        )

    def predict_video(
        self,
        video_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        frame_interval: int = 1,
        progress_callback: Optional[callable] = None
    ) -> List[DetectionResult]:
        """Process a road video file and optionally write annotated video output."""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Unable to open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        writer = None
        if output_path is not None:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(output_path), fourcc, fps / frame_interval, (width, height))

        results = []
        frame_idx = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = self.predict(frame_rgb)
                results.append(res)

                if writer is not None:
                    annotated_bgr = cv2.cvtColor(res.image, cv2.COLOR_RGB2BGR)
                    writer.write(annotated_bgr)

                if progress_callback and total_frames > 0:
                    progress_callback(frame_idx, total_frames)

            frame_idx += 1

        cap.release()
        if writer is not None:
            writer.release()

        return results
