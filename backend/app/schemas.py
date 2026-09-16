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
    dataset_name: str = "Kaggle: chitholian/annotated-potholes-dataset"
    total_images: int = 665
    damaged_images: int = 665
    undamaged_images: int = 0
    total_defects: int = 1739
    potholes_count: int = 1739
    cracks_count: int = 0
    other_count: int = 0
    avg_severity: float = 2.62
    composite_damage_score: float = 82.0
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
    dataset_name: str = "Kaggle: chitholian/annotated-potholes-dataset"
    ingestion_date: str = "2026-08-19"
    total_images: int = 665
    damaged_images: int = 665
    undamaged_images: int = 0
    total_boxes: int = 1739
    train_images: int = 498
    val_images: int = 99
    test_images: int = 68
    precision: float = 0.792
    recall: float = 0.718
    map50: float = 0.764
    map50_95: float = 0.438
    architecture: str = "YOLOv8s"
    epochs_trained: int = 100
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


# ── Civic pipeline ──────────────────────────────────────────────────────────

class GeocodeResultModel(BaseModel):
    road_name: str
    road: str = ""
    ward: str = ""
    city: str = ""
    state: str = ""
    postcode: str = ""
    country: str = ""
    display_name: str = ""
    osm_road_type: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None


class InspectionCreateRequest(BaseModel):
    filename: str
    road_name: str = Field(min_length=1, max_length=200)
    lat: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    lon: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    total_defects: int = Field(ge=0)
    severity_score: float = Field(ge=0.0, le=5.0)
    composite_damage_score: float = Field(ge=0.0, le=100.0)
    boxes: List[DetectionBoxModel]
    annotated_image: str
    # Filled by the browser from the reverse-geocode lookup when available; the
    # backend re-derives road_class and priority regardless.
    address: Optional[str] = None
    ward: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    osm_road_type: Optional[str] = None


class InspectionModel(BaseModel):
    id: int
    filename: str
    road_name: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    address: Optional[str] = None
    ward: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    osm_road_type: Optional[str] = None
    road_class: Optional[str] = None
    total_defects: int
    severity_score: float
    composite_damage_score: float
    patch_area_m2: Optional[float] = None
    priority: Optional[str] = None
    priority_label: Optional[str] = None
    priority_score: Optional[float] = None
    boxes: List[DetectionBoxModel]
    annotated_image: str
    created_at: float
    case_id: Optional[int] = None


class ContractorModel(BaseModel):
    id: int
    name: str
    specialty: str
    service_area: str
    rating: float = 4.0
    crew_count: int = 5


class PortalModel(BaseModel):
    code: str
    name: str
    authority: str
    department: str
    portal_url: str
    simulated: bool = True


class BoqLineModel(BaseModel):
    description: str
    unit: str
    quantity: float
    rate_inr: float
    amount_inr: float


class BoqModel(BaseModel):
    area_m2: float
    lines: List[BoqLineModel]
    subtotal_inr: float
    net_inr: float
    gst_inr: float
    total_inr: float


class BidModel(BaseModel):
    contractor_id: int
    contractor_name: str
    specialty: str
    service_area: str
    rating: float
    quoted_inr: float
    variance_pct: float
    promised_days: float


class AwardModel(BaseModel):
    contractor_id: int
    contractor_name: str
    specialty: str
    rating: float
    crew_count: int
    awarded_inr: Optional[float] = None
    promised_days: Optional[float] = None
    variance_pct: float = 0.0
    awarded_at: Optional[float] = None


class VerificationModel(BaseModel):
    filename: str
    defects_before: int
    defects_after: int
    remaining_ratio: float
    effectiveness_pct: float
    severity_after: float
    damage_score_after: float
    annotated_image: str = ""
    passed: bool
    checked_at: float
    attempts: int = 1


class PipelineEventModel(BaseModel):
    id: int
    case_id: Optional[int] = None
    inspection_id: Optional[int] = None
    stage: str
    actor: str
    title: str
    detail: str = ""
    created_at: float


class FindingViewModel(BaseModel):
    id: int
    filename: str
    road_name: str
    address: Optional[str] = None
    ward: Optional[str] = None
    city: Optional[str] = None
    road_class: str = "Local"
    lat: Optional[float] = None
    lon: Optional[float] = None
    total_defects: int
    severity_score: float
    composite_damage_score: float
    patch_area_m2: Optional[float] = None
    priority: Optional[str] = None
    created_at: float
    case_id: Optional[int] = None
    boxes: List[DetectionBoxModel]
    annotated_image: str = ""


class CaseViewModel(BaseModel):
    id: int
    status: str
    stage_index: int
    stage_label: str
    created_at: float
    total_potholes: int
    avg_severity: float
    severity_label: str
    severity_hex: str
    priority: Optional[str] = None
    priority_label: Optional[str] = None
    priority_score: Optional[float] = None
    patch_area_m2: Optional[float] = None
    estimate_inr: Optional[float] = None
    boq: Optional[BoqModel] = None
    portal: Optional[PortalModel] = None
    tracking_id: Optional[str] = None
    routing_note: Optional[str] = None
    officer: Optional[str] = None
    submitted_at: Optional[float] = None
    acknowledged_at: Optional[float] = None
    sla_hours: Optional[float] = None
    sla_due_at: Optional[float] = None
    sla_state: str
    hours_remaining: Optional[float] = None
    breached: bool = False
    tendered_at: Optional[float] = None
    bids: List[BidModel] = []
    awarded: Optional[AwardModel] = None
    repair_progress_pct: float = 0.0
    repair_sim_days: float = 0.0
    repaired_at: Optional[float] = None
    verification: Optional[VerificationModel] = None
    verified_at: Optional[float] = None
    closed_at: Optional[float] = None
    seconds_per_sim_day: float
    findings: List[FindingViewModel] = []
    events: List[PipelineEventModel] = []


class StageModel(BaseModel):
    key: str
    label: str
    actor: str


class PipelineStatsModel(BaseModel):
    total_findings: int
    unassigned_findings: int
    total_cases: int
    stage_counts: Dict[str, int]
    open_cases: int
    closed_cases: int
    sla_breached: int
    sla_at_risk: int
    potholes_reported: int
    potholes_repaired: int
    area_m2_reported: float
    estimated_inr: float
    committed_inr: float
    seconds_per_sim_day: float
    stages: List[StageModel]


class MapPointModel(BaseModel):
    id: int
    road_name: str
    address: str
    ward: str = ""
    road_class: str = "Local"
    lat: float
    lon: float
    total_defects: int
    severity: str
    severity_score: float
    confidence: float
    damage_score: float
    priority: str = "—"
    color_hex: str
    color_r: int
    color_g: int
    color_b: int
    case_id: Optional[int] = None
    case_status: str = "UNFILED"
    tracking_id: Optional[str] = None
    repaired: bool = False
    logged_at: float


class CaseCreateRequest(BaseModel):
    inspection_ids: List[int] = Field(min_length=1)


class AwardRequest(BaseModel):
    contractor_id: int
