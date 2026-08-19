from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict

class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool = True
    classes: List[str] = ["pothole"]

class SystemInfoResponse(BaseModel):
    status: str = "online"
    torch_version: str
    cuda_available: bool
    device: str
    models_loaded: List[str]
    models_available: Optional[List[str]] = None
    fine_tuned: Optional[bool] = True

class SamplesListResponse(BaseModel):
    samples: List[str]

class DetectionBoxModel(BaseModel):
    index: int
    code: str
    name: str
    category: str
    severity: str
    severity_score: float
    color: str
    confidence: float
    box: List[float]
    area: float

class CompanionDetectionItem(BaseModel):
    class_name: str = Field(alias="class")
    confidence: float
    bbox: List[float]
    area_pct: float
    severity: str

    model_config = ConfigDict(populate_by_name=True)

class CompanionImageResult(BaseModel):
    filename: str
    detections: List[CompanionDetectionItem]
    annotated_image: str

class DetectionResultResponse(BaseModel):
    success: bool = True
    inference_time_ms: float
    total_defects: int
    severity_score: float
    composite_damage_score: float
    boxes: List[DetectionBoxModel]
    annotated_image: str
    original_image: str
    road_mask: str = ""
    results: Optional[List[CompanionImageResult]] = None

class DashboardSummaryResponse(BaseModel):
    dataset_name: str = "Annotated Potholes Benchmark (Roboflow/Kaggle)"
    total_images: int = 665
    damaged_images: int = 665
    undamaged_images: int = 0
    total_defects: int = 1739
    potholes_count: int = 1739
    cracks_count: int = 0
    other_count: int = 0
    avg_severity: float = 2.62
    composite_damage_score: float = 82.0
    surveyed_area_m2: int = 665
    verified_pavement_m2: int = 665
    class_distribution: Dict[str, int] = {
        "pothole": 1739,
    }
    is_demo_data: bool = False

class GisDataPointModel(BaseModel):
    id: int
    damage_code: str
    damage_type: str
    category: str
    severity: str
    severity_score: float
    confidence: float
    municipality: str
    lat: float
    lon: float
    color_r: int
    color_g: int
    color_b: int
    color_hex: str

class DatasetStatsResponse(BaseModel):
    total_images: int = 665
    damaged_images: int = 665
    undamaged_images: int = 0
    total_boxes: int = 1739
    class_distribution: Dict[str, int] = {
        "pothole": 1739,
    }
    is_demo_data: bool = False

class TrainingLossEntry(BaseModel):
    epoch: int
    loss: float

class TrainingJobStatusResponse(BaseModel):
    status: str = "idle"
    progress: float = 0.0
    current_epoch: int = 0
    total_epochs: int = 0
    current_loss: float = 0.0
    losses: List[TrainingLossEntry] = []
    checkpoint_path: str = ""
    error: Optional[str] = None

class StartTrainingResultResponse(BaseModel):
    success: bool = True
    message: str = "Training completed or idle"
    epochs: Optional[int] = None
    architecture: Optional[str] = None

class UploadedItemModel(BaseModel):
    filename: str
    defects_found: int
    width: int
    height: int

class UploadPotholeImagesResponse(BaseModel):
    success: bool = True
    message: str = "Images uploaded and ingested successfully"
    dataset_path: str = "datasets/custom_potholes"
    items: List[UploadedItemModel] = []
