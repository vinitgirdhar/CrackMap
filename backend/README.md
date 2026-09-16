# CrackMap Backend Service

FastAPI REST backend serving the trained YOLOv8 pothole and road damage detection model.

## Directory Structure

```
backend/
├── app/
│   ├── cases.py        # Civic stage machine, reconciliation, case read model
│   ├── civic.py        # Portal routing, triage, SLA, bill of quantities, sim clock
│   ├── config.py       # Environment configuration and defaults
│   ├── db.py           # SQLite persistence and schema migrations
│   ├── detector.py     # YOLOv8 inference and image annotation engine
│   ├── geocode.py      # OpenStreetMap Nominatim reverse/forward geocoding
│   ├── main.py         # FastAPI routes, CORS, and endpoint handlers
│   ├── report_pdf.py   # Case dossier and completion certificate PDFs
│   └── schemas.py      # Pydantic request and response models
├── data/
│   └── crackmap.db     # Findings, cases, contractors, pipeline audit events
├── models/
│   └── best.pt         # Trained YOLOv8 pothole model weights
├── samples/            # Benchmark road imagery for demonstration
├── requirements.txt    # Python dependencies
└── README.md           # Documentation
```

## Setup & Running

### 1. Create a Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Server
Run from the `backend/` directory:
```bash
uvicorn app.main:app --reload --port 8000
```
Or from the project root:
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

## API Documentation & Endpoints

Once the server is running, interactive API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

- **`GET /api/health`**: Health status and loaded model classes.
- **`GET /api/system-info`**: PyTorch version, CPU/GPU accelerator status, and model metadata.
- **`POST /api/detect`**: Runs YOLOv8 inference on uploaded file(s) or preset sample name with configurable confidence threshold. Returns bounding boxes, severity rating, and base64 annotated frame.
- **`GET /api/samples`**: Lists available sample image filenames.
- **`GET /api/sample/{name}`**: Serves preset sample images.
- **`GET /api/dashboard-summary`**: Benchmark dataset statistics and defect summaries.
- **`GET /api/dataset-stats`**: Damage class distribution and model performance metrics.
- **`GET /api/gis-data`**: Every geolocated finding with the live stage of its civic case. Returns an empty list until something is logged — there is no demo fallback.

### Geocoding

Real OpenStreetMap Nominatim lookups, proxied server-side so the usage policy (identifying
User-Agent, one request per second, cached results) is honoured in one place.

- **`GET /api/geocode/reverse?lat&lon`**: Coordinate to street name, ward, city and OSM road type.
- **`GET /api/geocode/search?q&limit`**: Place or road name to candidate coordinates.

### Civic pipeline

- **`POST /api/inspections`**: Logs a detection as a civic finding — reverse-geocodes it, classifies the road, estimates the patch area and assigns a P1-P4 priority.
- **`GET /api/inspections`**: All logged findings.
- **`GET /api/contractors`**: The empanelled contractor panel with ratings and crew sizes.
- **`GET /api/civic/portals`**: Municipal grievance channels a case can route to (filing is simulated).
- **`GET /api/civic/stages`**: The nine pipeline stages and who owns each.
- **`GET /api/civic/stats`**: Board counters: per-stage counts, SLA pressure, potholes repaired, committed spend.
- **`GET /api/civic/events?limit`**: Persisted pipeline audit events, newest first.
- **`GET /api/civic/cases`**: All cases with live derived stages (evidence images omitted).
- **`GET /api/civic/cases/{id}`**: One case, including evidence images and its full audit trail.
- **`POST /api/civic/cases`**: Bundles findings into a triaged, costed grievance.
- **`POST /api/civic/cases/{id}/submit`**: Files it with the authority that owns the coordinate.
- **`POST /api/civic/cases/{id}/tender`**: Invites the contractor panel to quote against the BOQ.
- **`POST /api/civic/cases/{id}/award`**: Awards the work order to one bidder.
- **`POST /api/civic/cases/{id}/verify`**: Multipart after-photo — the detector re-scores the repair and either passes it or returns it as rework.
- **`POST /api/civic/cases/{id}/close`**: Closes a verified case and releases the certificate.

Three transitions have no endpoint because nobody triggers them: portal acknowledgement, crew
mobilisation and repair completion are derived from timestamps and persisted whenever a case is
read (`cases.reconcile`).

### Deliverables

- **`GET /api/civic/cases/{id}/dossier.pdf`**: Filing record, photographic evidence, priced BOQ, re-inspection result and audit trail.
- **`GET /api/civic/cases/{id}/certificate.pdf`**: Completion certificate; `409` until the re-inspection passes.
- **`GET /api/civic/cases/{id}/export.json`**: Whole case object for municipal data exchange.
- **`GET /api/civic/cases/{id}/export.csv`**: Defect inventory, one row per detected pothole.

### Archived training stubs

Kept for API compatibility; the UI moved to `front-end/_archive/`.

- **`GET /api/train-status`**, **`POST /api/train-model`**, **`POST /api/upload-pothole-images`**

## Configuration

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `MODEL_PATH` | `backend/models/best.pt` | YOLOv8 weights |
| `SAMPLES_DIR` | `backend/samples` | Benchmark imagery |
| `DB_PATH` | `backend/data/crackmap.db` | Findings, cases, contractors, audit events |
| `SIM_SECONDS_PER_DAY` | `12.0` | Wall-clock seconds per simulated municipal working day. Portal acknowledgement, crew mobilisation, repair progress and SLA windows all elapse on this clock. Raise toward `86400` for real time. |
| `CONF_THRESHOLD` | `0.35` | Default detection confidence |
| `IOU_THRESHOLD` | `0.5` | Default NMS IoU |
| `IMGSZ` | `640` | Inference image size |
| `ALLOWED_ORIGINS` | `localhost:3000,127.0.0.1:3000,localhost:8000` | CORS allowlist |

## Module self-checks

`civic.py`, `db.py`, `geocode.py` and `report_pdf.py` each carry a runnable assertion-based
self-check, useful for isolating a layer without booting the app:

```bash
python -m backend.app.civic
python -m backend.app.db
python -m backend.app.geocode
python -m backend.app.report_pdf
```
