import csv
import io
import json
import os
import time
from pathlib import Path
from typing import List, Optional

import torch
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from PIL import Image

from . import cases, civic, db, geocode, report_pdf
from .config import settings
from .detector import detector_instance
from .schemas import (
    AwardRequest,
    CaseCreateRequest,
    CaseViewModel,
    CompanionImageResult,
    CompletedRepairModel,
    ContractorModel,
    DashboardSummaryResponse,
    DatasetStatsResponse,
    DetectionResultResponse,
    GeocodeResultModel,
    HealthResponse,
    InspectionCreateRequest,
    InspectionModel,
    MapPointModel,
    PipelineEventModel,
    PipelineStatsModel,
    PortalModel,
    SamplesListResponse,
    StageModel,
    StartTrainingResultResponse,
    SystemInfoResponse,
    TrainingJobStatusResponse,
    UploadedItemModel,
    UploadPotholeImagesResponse,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FastAPI service for YOLOv8 pothole detection and the civic repair pipeline",
)

db.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health & system ─────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {"service": settings.PROJECT_NAME, "status": "online", "docs": "/docs"}


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


# ── Samples & inference ─────────────────────────────────────────────────────

@app.get("/api/samples", response_model=SamplesListResponse, tags=["Samples"])
async def list_samples():
    samples_path = Path(settings.SAMPLES_DIR)
    if not samples_path.exists():
        return SamplesListResponse(samples=[])

    allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
    sample_files = sorted(
        f.name for f in samples_path.iterdir() if f.is_file() and f.suffix.lower() in allowed_exts
    )
    return SamplesListResponse(samples=sample_files)


@app.get("/api/sample/{name}", tags=["Samples"])
async def get_sample_image(name: str):
    safe_name = os.path.basename(name)  # block path traversal
    sample_path = Path(settings.SAMPLES_DIR) / safe_name
    if not sample_path.exists() or not sample_path.is_file():
        raise HTTPException(status_code=404, detail=f"Sample '{safe_name}' not found")
    return FileResponse(sample_path)


def _run_detection(image: Image.Image, filename: str, conf: float, iou: float, size: int) -> DetectionResultResponse:
    return detector_instance.detect(image=image, filename=filename, conf=conf, iou=iou, imgsz=size)


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

    # Normalize conf if passed on a 0-100 scale (e.g. from UI sliders)
    if conf > 1.0:
        conf = conf / 100.0

    if files and len(files) > 1:
        combined_results: List[CompanionImageResult] = []
        last_single_result: Optional[DetectionResultResponse] = None

        for f in files:
            try:
                contents = await f.read()
                res = _run_detection(Image.open(io.BytesIO(contents)), f.filename or "image.jpg", conf, iou, size)
                if res.results:
                    combined_results.extend(res.results)
                last_single_result = res
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to process file '{f.filename}': {e}")

        if last_single_result:
            last_single_result.results = combined_results
            return last_single_result
        raise HTTPException(status_code=400, detail="No valid images found in batch upload")

    upload_target = file or (files[0] if files and len(files) == 1 else None)
    if upload_target is not None:
        try:
            contents = await upload_target.read()
            return _run_detection(
                Image.open(io.BytesIO(contents)), upload_target.filename or "uploaded.jpg", conf, iou, size
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process uploaded image: {e}")

    if sample_name:
        safe_name = os.path.basename(sample_name)
        sample_path = Path(settings.SAMPLES_DIR) / safe_name
        if not sample_path.exists():
            raise HTTPException(status_code=404, detail=f"Sample '{safe_name}' not found")
        try:
            return _run_detection(Image.open(sample_path), safe_name, conf, iou, size)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process sample image: {e}")

    raise HTTPException(
        status_code=400,
        detail="Must provide either an uploaded image file, multiple files, or a sample_name",
    )


# ── Dataset analytics ───────────────────────────────────────────────────────

@app.get("/api/dashboard-summary", response_model=DashboardSummaryResponse, tags=["Analytics"])
async def get_dashboard_summary():
    return DashboardSummaryResponse()


@app.get("/api/dataset-stats", response_model=DatasetStatsResponse, tags=["Analytics"])
async def get_dataset_stats():
    return DatasetStatsResponse()


# ── Geocoding ───────────────────────────────────────────────────────────────

@app.get("/api/geocode/reverse", response_model=GeocodeResultModel, tags=["Geocoding"])
async def reverse_geocode(
    lat: float = Query(ge=-90.0, le=90.0), lon: float = Query(ge=-180.0, le=180.0)
):
    """Coordinate -> real OpenStreetMap street name, ward, city and road class."""
    try:
        return GeocodeResultModel(**geocode.reverse(lat, lon))
    except geocode.GeocodeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/api/geocode/search", response_model=List[GeocodeResultModel], tags=["Geocoding"])
async def search_geocode(q: str = Query(min_length=2, max_length=200), limit: int = Query(5, ge=1, le=10)):
    """Road or place name -> candidate real-world coordinates."""
    try:
        return [GeocodeResultModel(**item) for item in geocode.search(q, limit)]
    except geocode.GeocodeError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── Map ─────────────────────────────────────────────────────────────────────

@app.get("/api/gis-data", response_model=List[MapPointModel], tags=["GIS"])
async def get_gis_data():
    """Every geolocated finding with the live stage of its municipal case.

    Returns an empty list until something is actually logged — no demo pins, so
    what the map shows is always real inspection output.
    """
    return [MapPointModel(**point) for point in cases.map_points()]


# ── Findings ────────────────────────────────────────────────────────────────

@app.post("/api/inspections", response_model=InspectionModel, tags=["Civic Pipeline"])
async def log_inspection(payload: InspectionCreateRequest):
    """Log a detection as a civic finding: geocode it, classify the road, triage it."""
    data = payload.model_dump()
    data["boxes"] = [box.model_dump() for box in payload.boxes]

    # Best-effort enrichment. A geocoder outage must never lose a field report,
    # so every failure falls back to whatever the client already supplied.
    if data.get("lat") is not None and data.get("lon") is not None and not data.get("address"):
        try:
            place = geocode.reverse(data["lat"], data["lon"])
            data["address"] = place["display_name"] or place["road_name"]
            data["ward"] = data.get("ward") or place["ward"]
            data["city"] = data.get("city") or place["city"]
            data["state"] = data.get("state") or place["state"]
            data["osm_road_type"] = data.get("osm_road_type") or place["osm_road_type"]
        except geocode.GeocodeError as e:
            print(f"[geocode] reverse lookup failed, logging without address: {e}")

    data["road_class"] = civic.classify_road(data.get("osm_road_type"))
    data["patch_area_m2"] = civic.patch_area_m2(data["boxes"])
    triage = civic.assess_priority(data["severity_score"], data["total_defects"], data["road_class"])
    data["priority"] = triage["priority"]
    data["priority_label"] = triage["priority_label"]
    data["priority_score"] = triage["priority_score"]

    row = db.create_inspection(data)
    db.log_event(
        "DRAFT",
        "Field Inspector",
        f"Finding #{row['id']} logged at {row['road_name']}",
        f"{row['total_defects']} pothole(s) detected, severity {row['severity_score']}/5 on a "
        f"{row['road_class']} road. Triaged {triage['priority']} "
        f"(score {triage['priority_score']}). Estimated patch area {row['patch_area_m2']} m².",
        inspection_id=row["id"],
        at=row["created_at"],
    )
    return InspectionModel(**row)


@app.get("/api/inspections", response_model=List[InspectionModel], tags=["Civic Pipeline"])
async def list_inspections():
    return [InspectionModel(**row) for row in db.list_inspections()]


@app.get("/api/contractors", response_model=List[ContractorModel], tags=["Civic Pipeline"])
async def list_contractors():
    return [ContractorModel(**row) for row in db.list_contractors()]


# ── Civic pipeline: reference data ──────────────────────────────────────────

@app.get("/api/civic/portals", response_model=List[PortalModel], tags=["Civic Pipeline"])
async def list_portals():
    """The municipal grievance channels cases can be routed to (filing simulated)."""
    return [
        PortalModel(
            code=p["code"],
            name=p["name"],
            authority=p["authority"],
            department=p["department"],
            portal_url=p["portal_url"],
        )
        for p in [*civic.PORTALS, civic.FALLBACK_PORTAL]
    ]


@app.get("/api/civic/stages", response_model=List[StageModel], tags=["Civic Pipeline"])
async def list_stages():
    return [StageModel(**stage) for stage in civic.STAGES]


@app.get("/api/civic/stats", response_model=PipelineStatsModel, tags=["Civic Pipeline"])
async def get_pipeline_stats():
    return PipelineStatsModel(**cases.pipeline_stats())


@app.get("/api/civic/events", response_model=List[PipelineEventModel], tags=["Civic Pipeline"])
async def list_pipeline_events(limit: int = Query(60, ge=1, le=500)):
    cases.reconcile_all()
    return [PipelineEventModel(**event) for event in db.list_events(limit=limit)]


# ── Civic pipeline: cases ───────────────────────────────────────────────────

def _require_case(case_id: int, include_images: bool = True) -> dict:
    view = cases.get_case_view(case_id, include_images=include_images)
    if view is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return view


@app.get("/api/civic/completed", response_model=List[CompletedRepairModel], tags=["Civic Pipeline"])
async def list_completed_repairs():
    """Before/after record for every verified repair.

    Separate from the board list because it carries the evidence image pair —
    the frontend fetches it only when the set of completed cases changes.
    """
    return [CompletedRepairModel(**record) for record in cases.completed_records()]


@app.get("/api/civic/cases", response_model=List[CaseViewModel], tags=["Civic Pipeline"])
async def list_cases():
    """All cases with live derived stages. Evidence images are omitted here —
    fetch a single case for those."""
    return [CaseViewModel(**view) for view in cases.list_case_views(include_images=False)]


@app.get("/api/civic/cases/{case_id}", response_model=CaseViewModel, tags=["Civic Pipeline"])
async def get_case(case_id: int):
    view = cases.get_case_view(case_id)
    if view is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return CaseViewModel(**view)


@app.post("/api/civic/cases", response_model=CaseViewModel, tags=["Civic Pipeline"])
async def create_case(payload: CaseCreateRequest):
    try:
        case = cases.create_case(payload.inspection_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CaseViewModel(**_require_case(case["id"]))


def _case_action_response(case_id: int, result: Optional[dict]) -> CaseViewModel:
    """Every stage action answers with the freshly reconciled case view."""
    if result is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return CaseViewModel(**_require_case(case_id))


@app.post("/api/civic/cases/{case_id}/submit", response_model=CaseViewModel, tags=["Civic Pipeline"])
async def submit_case(case_id: int):
    """File the case with the municipal portal owning its coordinates."""
    return _case_action_response(case_id, cases.submit_case(case_id))


@app.post("/api/civic/cases/{case_id}/tender", response_model=CaseViewModel, tags=["Civic Pipeline"])
async def tender_case(case_id: int):
    """Invite the empanelled contractor panel to quote against the BOQ."""
    return _case_action_response(case_id, cases.tender_case(case_id))


@app.post("/api/civic/cases/{case_id}/award", response_model=CaseViewModel, tags=["Civic Pipeline"])
async def award_case(case_id: int, payload: AwardRequest):
    try:
        result = cases.award_case(case_id, payload.contractor_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _case_action_response(case_id, result)


@app.post("/api/civic/cases/{case_id}/verify", response_model=CaseViewModel, tags=["Civic Pipeline"])
async def verify_case(case_id: int, file: UploadFile = File(...)):
    """Re-inspect a repaired road: run the detector on an after-photo and judge the work."""
    if cases.get_case_view(case_id, include_images=False) is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    try:
        contents = await file.read()
        detection = _run_detection(
            Image.open(io.BytesIO(contents)),
            file.filename or "after.jpg",
            settings.DEFAULT_CONF,
            settings.DEFAULT_IOU,
            settings.DEFAULT_IMGSZ,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process the after-photo: {e}")

    result = cases.verify_case(case_id, detection.model_dump(), file.filename or "after.jpg")
    return _case_action_response(case_id, result)


@app.post("/api/civic/cases/{case_id}/close", response_model=CaseViewModel, tags=["Civic Pipeline"])
async def close_case(case_id: int):
    return _case_action_response(case_id, cases.close_case(case_id))


# ── Civic pipeline: deliverables ────────────────────────────────────────────

@app.get("/api/civic/cases/{case_id}/dossier.pdf", tags=["Deliverables"])
async def download_dossier(case_id: int):
    """Full case dossier: filing record, evidence, BOQ, re-inspection, audit trail."""
    view = _require_case(case_id)
    return Response(
        content=report_pdf.generate_dossier_pdf(view),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="crackmap_case_{case_id}_dossier.pdf"'},
    )


@app.get("/api/civic/cases/{case_id}/certificate.pdf", tags=["Deliverables"])
async def download_certificate(case_id: int):
    """Repair completion certificate — available once an AI re-inspection passes."""
    view = _require_case(case_id)
    if view["status"] not in ("VERIFIED", "CLOSED"):
        raise HTTPException(
            status_code=409,
            detail="A completion certificate is only issued after the re-inspection passes",
        )
    return Response(
        content=report_pdf.generate_certificate_pdf(view),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="crackmap_case_{case_id}_certificate.pdf"'},
    )


@app.get("/api/civic/cases/{case_id}/export.json", tags=["Deliverables"])
async def export_case_json(case_id: int):
    """Machine-readable case record for municipal open-data exchange."""
    view = _require_case(case_id, include_images=False)
    payload = {
        "schema": "crackmap.civic.case/1",
        "exported_at": time.time(),
        "filing_is_simulated": True,
        "case": view,
    }
    return Response(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="crackmap_case_{case_id}.json"'},
    )


@app.get("/api/civic/cases/{case_id}/export.csv", tags=["Deliverables"])
async def export_case_csv(case_id: int):
    """Defect inventory as CSV — one row per detected pothole."""
    view = _require_case(case_id, include_images=False)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "case_id", "tracking_id", "case_status", "priority", "finding_id", "road_name",
            "address", "ward", "road_class", "lat", "lon", "defect_index", "defect_code",
            "defect_name", "severity", "confidence_pct", "box_x1", "box_y1", "box_x2", "box_y2",
            "area_px2", "logged_at",
        ]
    )
    for finding in view["findings"]:
        for box in finding["boxes"]:
            writer.writerow(
                [
                    view["id"], view["tracking_id"] or "", view["status"], view["priority"] or "",
                    finding["id"], finding["road_name"], finding.get("address") or "",
                    finding.get("ward") or "", finding["road_class"], finding["lat"], finding["lon"],
                    box["index"], box["code"], box["name"], box["severity"], box["confidence"],
                    *box["box"], box["area"], finding["created_at"],
                ]
            )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="crackmap_case_{case_id}_defects.csv"'},
    )


# ── Archived training stubs ─────────────────────────────────────────────────
# Left in place for API compatibility; the UI moved to front-end/_archive/.

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


@app.get("/api/train-status", response_model=TrainingJobStatusResponse, tags=["Training (Archived)"])
async def get_training_status():
    return TrainingJobStatusResponse()


@app.post("/api/upload-pothole-images", response_model=UploadPotholeImagesResponse, tags=["Training (Archived)"])
async def upload_pothole_images(files: List[UploadFile] = File(...)):
    items = [
        UploadedItemModel(filename=f.filename or "unknown.jpg", defects_found=1, width=640, height=480)
        for f in files
    ]
    return UploadPotholeImagesResponse(
        success=True,
        message=f"Successfully ingested and auto-labeled {len(files)} custom road images",
        dataset_path="datasets/custom_potholes",
        items=items,
    )
