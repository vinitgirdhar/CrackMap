# CrackMap Backend Service

FastAPI REST backend serving the trained YOLOv8 pothole and road damage detection model.

## Directory Structure

```
backend/
├── app/
│   ├── config.py       # Environment configuration and defaults
│   ├── detector.py     # YOLOv8 inference and image annotation engine
│   ├── main.py         # FastAPI routes, CORS, and endpoint handlers
│   └── schemas.py      # Pydantic request and response models
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
- **`GET /api/dashboard-summary`**: Live survey statistics and defect summaries.
- **`GET /api/gis-data`**: Geotagged pavement defect coordinates for GIS mapping.
- **`GET /api/dataset-stats`**: Damage class distribution metrics.
- **`GET /api/train-status`**: Status for model fine-tuning jobs.
- **`POST /api/train-model`**: Initiates training session (stub mode).
- **`POST /api/upload-pothole-images`**: Ingests custom road images for fine-tuning.
