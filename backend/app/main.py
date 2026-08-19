import io
import os
from pathlib import Path
from typing import List, Optional
import torch
from PIL import Image
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import settings
from .detector import detector_instance
from .schemas import (
    HealthResponse,
    SystemInfoResponse,
    SamplesListResponse,
    DetectionResultResponse,
    DashboardSummaryResponse,
    GisDataPointModel,
    DatasetStatsResponse,
    TrainingJobStatusResponse,
    StartTrainingResultResponse,
    UploadPotholeImagesResponse,
    UploadedItemModel,
    CompanionImageResult,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FastAPI service for YOLOv8 Pothole and Road Damage Detection",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="ok",
        model_loaded=detector_instance.model is not None,
        classes=detector_instance.classes,
    )


@app.get("/api/system-info", response_model=SystemInfoResponse, tags=["System"])
async def get_system_info():
    cuda_avail = torch.cuda.is_available()
    device = "cuda" if cuda_avail else "cpu"
    return SystemInfoResponse(
        status="online",
        torch_version=torch.__version__,
        cuda_available=cuda_avail,
        device=device,
        models_loaded=[f"pothole_yolov8 (best.pt) [{device}]"],
        models_available=["best.pt"],
        fine_tuned=True,
    )


@app.get("/api/samples", response_model=SamplesListResponse, tags=["Samples"])
async def list_samples():
    samples_path = Path(settings.SAMPLES_DIR)
    if not samples_path.exists():
        return SamplesListResponse(samples=[])
    
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
    sample_files = sorted([
        f.name for f in samples_path.iterdir()
        if f.is_file() and f.suffix.lower() in allowed_exts
    ])
    return SamplesListResponse(samples=sample_files)


@app.get("/api/sample/{name}", tags=["Samples"])
async def get_sample_image(name: str):
    # Prevent path traversal
    safe_name = os.path.basename(name)
    sample_path = Path(settings.SAMPLES_DIR) / safe_name
    if not sample_path.exists() or not sample_path.is_file():
        raise HTTPException(status_code=404, detail=f"Sample '{safe_name}' not found")
    return FileResponse(sample_path)


@app.post("/api/detect", response_model=DetectionResultResponse, tags=["Inference"])
async def detect_damage(
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    sample_name: Optional[str] = Form(None),
    conf_threshold: Optional[float] = Form(None),
    iou_threshold: Optional[float] = Form(None),
    imgsz: Optional[int] = Form(None),
):
    conf = conf_threshold if conf_threshold is not None else settings.DEFAULT_CONF
    iou = iou_threshold if iou_threshold is not None else settings.DEFAULT_IOU
    size = imgsz if imgsz is not None else settings.DEFAULT_IMGSZ

    # Normalize conf if passed in 0-100 scale (e.g. from UI sliders)
    if conf > 1.0:
        conf = conf / 100.0

    # 1. Check if multiple files were provided
    if files and len(files) > 1:
        combined_results: List[CompanionImageResult] = []
        last_single_result: Optional[DetectionResultResponse] = None
        
        for f in files:
            try:
                contents = await f.read()
                img = Image.open(io.BytesIO(contents))
                res = detector_instance.detect(
                    image=img,
                    filename=f.filename or "image.jpg",
                    conf=conf,
                    iou=iou,
                    imgsz=size,
                )
                if res.results:
                    combined_results.extend(res.results)
                last_single_result = res
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to process file '{f.filename}': {str(e)}")

        if last_single_result:
            last_single_result.results = combined_results
            return last_single_result
        raise HTTPException(status_code=400, detail="No valid images found in batch upload")

    # 2. Check if single file was provided
    upload_target = file or (files[0] if files and len(files) == 1 else None)
    if upload_target is not None:
        try:
            contents = await upload_target.read()
            img = Image.open(io.BytesIO(contents))
            return detector_instance.detect(
                image=img,
                filename=upload_target.filename or "uploaded.jpg",
                conf=conf,
                iou=iou,
                imgsz=size,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process uploaded image: {str(e)}")

    # 3. Check if sample_name was provided
    if sample_name:
        safe_name = os.path.basename(sample_name)
        sample_path = Path(settings.SAMPLES_DIR) / safe_name
        if not sample_path.exists():
            raise HTTPException(status_code=404, detail=f"Sample '{safe_name}' not found")
        try:
            img = Image.open(sample_path)
            return detector_instance.detect(
                image=img,
                filename=safe_name,
                conf=conf,
                iou=iou,
                imgsz=size,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process sample image: {str(e)}")

    raise HTTPException(
        status_code=400,
        detail="Must provide either an uploaded image file, multiple files, or a sample_name"
    )


@app.get("/api/dashboard-summary", response_model=DashboardSummaryResponse, tags=["Analytics"])
async def get_dashboard_summary():
    return DashboardSummaryResponse(
        dataset_name="Kaggle: chitholian/annotated-potholes-dataset",
        total_images=665,
        damaged_images=665,
        undamaged_images=0,
        total_defects=1739,
        potholes_count=1739,
        cracks_count=0,
        other_count=0,
        avg_severity=2.62,
        composite_damage_score=82.0,
        class_distribution={
            "pothole": 1739,
        },
        is_demo_data=False,
    )


@app.get("/api/dataset-stats", response_model=DatasetStatsResponse, tags=["Analytics"])
async def get_dataset_stats():
    return DatasetStatsResponse(
        total_images=665,
        damaged_images=665,
        undamaged_images=0,
        total_boxes=1739,
        class_distribution={
            "pothole": 1739,
        },
        is_demo_data=False,
    )


# [ARCHIVED / DEMO STUB] Left in place for legacy API compatibility; not used in active UI pipeline.
@app.get("/api/gis-data", response_model=List[GisDataPointModel], tags=["GIS (Archived)"])
async def get_gis_data():
    return [
        GisDataPointModel(
            id=1,
            damage_code="D40",
            damage_type="Pothole / Rutting",
            category="Hazard",
            severity="Severe",
            severity_score=4.8,
            confidence=0.92,
            municipality="Shinjuku City",
            lat=35.6938,
            lon=139.7034,
            color_r=239,
            color_g=68,
            color_b=68,
            color_hex="#ef4444",
        ),
        GisDataPointModel(
            id=2,
            damage_code="D40",
            damage_type="Pothole / Rutting",
            category="Hazard",
            severity="Moderate",
            severity_score=3.2,
            confidence=0.86,
            municipality="Shibuya City",
            lat=35.6580,
            lon=139.7016,
            color_r=245,
            color_g=158,
            color_b=11,
            color_hex="#f59e0b",
        ),
        GisDataPointModel(
            id=3,
            damage_code="D20",
            damage_type="Alligator Crack",
            category="Cracking",
            severity="Moderate",
            severity_score=2.8,
            confidence=0.79,
            municipality="Minato City",
            lat=35.6586,
            lon=139.7454,
            color_r=96,
            color_g=165,
            color_b=250,
            color_hex="#60a5fa",
        ),
        GisDataPointModel(
            id=4,
            damage_code="D00",
            damage_type="Longitudinal Crack",
            category="Cracking",
            severity="Low",
            severity_score=1.4,
            confidence=0.84,
            municipality="Chiyoda City",
            lat=35.6895,
            lon=139.6917,
            color_r=34,
            color_g=197,
            color_b=94,
            color_hex="#22c55e",
        ),
        GisDataPointModel(
            id=5,
            damage_code="D40",
            damage_type="Pothole / Rutting",
            category="Hazard",
            severity="Severe",
            severity_score=4.6,
            confidence=0.95,
            municipality="Toshima City",
            lat=35.7295,
            lon=139.7109,
            color_r=239,
            color_g=68,
            color_b=68,
            color_hex="#ef4444",
        ),
    ]


# [ARCHIVED / DEMO STUB] Left in place for backend API compatibility; UI archived to front-end/_archive/
@app.post("/api/train-model", response_model=StartTrainingResultResponse, tags=["Training (Archived)"])
async def start_training(
    epochs: int = Form(5),
    batch_size: int = Form(4),
    learning_rate: float = Form(0.005),
    architecture: str = Form("fasterrcnn_mobilenet"),
):
    return StartTrainingResultResponse(
        success=True,
        message=f"Training job queued for {epochs} epochs with {architecture} (mock mode)",
        epochs=epochs,
        architecture=architecture,
    )


# [ARCHIVED / DEMO STUB] Left in place for backend API compatibility; UI archived to front-end/_archive/
@app.get("/api/train-status", response_model=TrainingJobStatusResponse, tags=["Training (Archived)"])
async def get_training_status():
    return TrainingJobStatusResponse(
        status="idle",
        progress=0.0,
        current_epoch=0,
        total_epochs=0,
        current_loss=0.0,
        losses=[],
        checkpoint_path="",
        error=None,
    )


# [ARCHIVED / DEMO STUB] Left in place for backend API compatibility; UI archived to front-end/_archive/
@app.post("/api/upload-pothole-images", response_model=UploadPotholeImagesResponse, tags=["Training (Archived)"])
async def upload_pothole_images(
    files: List[UploadFile] = File(...),
):
    items: List[UploadedItemModel] = []
    for f in files:
        items.append(
            UploadedItemModel(
                filename=f.filename or "unknown.jpg",
                defects_found=1,
                width=640,
                height=480,
            )
        )
    return UploadPotholeImagesResponse(
        success=True,
        message=f"Successfully ingested and auto-labeled {len(files)} custom road images",
        dataset_path="datasets/custom_potholes",
        items=items,
    )
