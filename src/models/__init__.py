"""Modern PyTorch and Hybrid Road Damage Detection models, training, inference, and evaluation."""
from .detector import build_road_damage_detector, RoadDamageDetectorNet
from .inference import RoadDamageInferenceEngine, DetectionResult
from .advanced_detector import AdvancedRoadDamageDetector
from .train import train_road_damage_model
from .evaluate import evaluate_detector, compute_iou, calculate_map

__all__ = [
    "build_road_damage_detector",
    "RoadDamageDetectorNet",
    "RoadDamageInferenceEngine",
    "AdvancedRoadDamageDetector",
    "DetectionResult",
    "train_road_damage_model",
    "evaluate_detector",
    "compute_iou",
    "calculate_map",
]
