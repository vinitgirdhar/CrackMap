import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert "pothole" in data["classes"]

def test_system_info():
    res = client.get("/api/system-info")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "device" in data
    assert len(data["models_loaded"]) > 0

def test_samples():
    res = client.get("/api/samples")
    assert res.status_code == 200
    data = res.json()
    assert "samples" in data
    assert len(data["samples"]) > 0

def test_detect_from_sample():
    res = client.post("/api/detect", data={"sample_name": "sample_01.jpg", "conf_threshold": "0.35"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "inference_time_ms" in data
    assert "annotated_image" in data
    assert data["annotated_image"].startswith("data:image/jpeg;base64,")
    assert "original_image" in data
    assert data["original_image"].startswith("data:image/jpeg;base64,")
    assert isinstance(data["boxes"], list)
    assert "composite_damage_score" in data
    assert "pci_score" not in data

def test_dashboard_summary():
    res = client.get("/api/dashboard-summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_images"] == 665
    assert data["total_defects"] == 1739
    assert "class_distribution" in data
    assert "pothole" in data["class_distribution"]
    assert "Roboflow" not in data["dataset_name"]
    assert "chitholian/annotated-potholes-dataset" in data["dataset_name"]
    assert "surveyed_area_m2" not in data
    assert "verified_pavement_m2" not in data

def test_gis_data():
    res = client.get("/api/gis-data")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "lat" in data[0]
    assert "lon" in data[0]

def test_dataset_stats():
    res = client.get("/api/dataset-stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_boxes" in data

def test_training_endpoints():
    res = client.get("/api/train-status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "idle"

    res = client.post("/api/train-model", data={"epochs": "5", "batch_size": "4", "learning_rate": "0.005", "architecture": "fasterrcnn_mobilenet"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
