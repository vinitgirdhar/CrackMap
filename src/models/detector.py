"""
PyTorch Object Detection Model Architectures for Road Damage Detection.
Supports MobileNetV3-FPN and ResNet50 Faster R-CNN backbones with configurable classes.
"""

from typing import Optional, Dict, Any
import torch
import torch.nn as nn
import torchvision
from torchvision.models.detection import (
    fasterrcnn_mobilenet_v3_large_fpn,
    fasterrcnn_resnet50_fpn,
    ssdlite320_mobilenet_v3_large,
    FasterRCNN_MobileNet_V3_Large_FPN_Weights,
    SSDLite320_MobileNet_V3_Large_Weights,
)
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.ssdlite import SSDLiteClassificationHead

from src.config import CLASS_NAMES


class RoadDamageDetectorNet(nn.Module):
    """Road Damage Detector wrapper around Torchvision detection models."""

    def __init__(
        self,
        architecture: str = "fasterrcnn_mobilenet",
        num_classes: int = len(CLASS_NAMES) + 1,  # +1 for background class 0
        pretrained_backbone: bool = True
    ):
        super().__init__()
        self.architecture = architecture
        self.num_classes = num_classes

        if architecture == "fasterrcnn_mobilenet":
            weights = FasterRCNN_MobileNet_V3_Large_FPN_Weights.DEFAULT if pretrained_backbone else None
            self.model = fasterrcnn_mobilenet_v3_large_fpn(weights=weights)
            in_features = self.model.roi_heads.box_predictor.cls_score.in_features
            self.model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

        elif architecture == "ssdlite_mobilenet":
            weights = SSDLite320_MobileNet_V3_Large_Weights.DEFAULT if pretrained_backbone else None
            self.model = ssdlite320_mobilenet_v3_large(weights=weights)
            in_channels = [c for c in self.model.head.classification_head.module_list]
            num_anchors = self.model.anchor_generator.num_anchors_per_location()
            self.model.head.classification_head = SSDLiteClassificationHead(
                in_channels=self.model.head.classification_head.in_channels,
                num_anchors=num_anchors,
                num_classes=num_classes,
                norm_layer=nn.BatchNorm2d
            )

        elif architecture == "fasterrcnn_resnet50":
            self.model = fasterrcnn_resnet50_fpn(weights=None)
            in_features = self.model.roi_heads.box_predictor.cls_score.in_features
            self.model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

        else:
            raise ValueError(f"Unsupported architecture: {architecture}")

    def forward(self, images, targets=None):
        return self.model(images, targets)


def build_road_damage_detector(
    architecture: str = "fasterrcnn_mobilenet",
    num_classes: int = len(CLASS_NAMES) + 1,
    checkpoint_path: Optional[str] = None,
    device: str = "cpu"
) -> RoadDamageDetectorNet:
    """Build and initialize detector with optional pre-trained weights."""
    model = RoadDamageDetectorNet(architecture=architecture, num_classes=num_classes)
    
    if checkpoint_path is not None:
        checkpoint = torch.load(checkpoint_path, map_location=device)
        if "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)
        print(f"Loaded weights from {checkpoint_path}")

    model.to(device)
    return model
