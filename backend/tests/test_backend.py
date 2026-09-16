import time

import pytest
from fastapi.testclient import TestClient

from backend.app import civic, db
from backend.app.config import settings


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """Isolated database per test run, and a fast simulated clock so the
    time-driven stages complete inside a test."""
    settings.DB_PATH = str(tmp_path_factory.mktemp("civic") / "test.db")
    settings.SIM_SECONDS_PER_DAY = 0.05
    from backend.app.main import app

    db.init_db()
    with TestClient(app) as test_client:
        yield test_client


def _finding_payload(**overrides):
    payload = {
        "filename": "road_001.jpg",
        "road_name": "Hill Road, Bandra West",
        # Inside the MCGM bounding box, so routing is deterministic.
        "lat": 19.0596,
        "lon": 72.8295,
        "address": "Hill Road, Bandra West, Mumbai",
        "ward": "Bandra West",
        "city": "Mumbai",
        "osm_road_type": "secondary",
        "total_defects": 4,
        "severity_score": 4.2,
        "composite_damage_score": 38.0,
        "boxes": [
            {
                "index": i,
                "code": "D40",
                "name": "Pothole",
                "category": "Pothole / Rutting",
                "severity": "Severe",
                "severity_score": 5.0,
                "color": "#ef4444",
                "confidence": 91.2,
                "box": [10.0, 10.0, 90.0, 90.0],
                "area": 6400.0,
            }
            for i in range(1, 5)
        ],
        "annotated_image": "data:image/jpeg;base64,abc123",
    }
    payload.update(overrides)
    return payload


def _await_stage(client, case_id, expected, timeout=6.0):
    """Poll until the clock-driven reconciliation reaches `expected`."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        case = client.get(f"/api/civic/cases/{case_id}").json()
        if case["status"] == expected:
            return case
        time.sleep(0.05)
    pytest.fail(f"case {case_id} stuck at {case['status']}, expected {expected}")


# ── Health, system, samples, inference ──────────────────────────────────────

def test_health(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert "pothole" in data["classes"]


def test_system_info(client):
    data = client.get("/api/system-info").json()
    assert data["status"] == "online"
    assert "device" in data
    assert len(data["models_loaded"]) > 0


def test_samples(client):
    data = client.get("/api/samples").json()
    assert len(data["samples"]) > 0


def test_detect_from_sample(client):
    sample_name = client.get("/api/samples").json()["samples"][0]
    res = client.post("/api/detect", data={"sample_name": sample_name, "conf_threshold": "0.35"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["annotated_image"].startswith("data:image/jpeg;base64,")
    assert data["original_image"].startswith("data:image/jpeg;base64,")
    assert isinstance(data["boxes"], list)
    assert "composite_damage_score" in data
    assert "pci_score" not in data


def test_dashboard_summary(client):
    data = client.get("/api/dashboard-summary").json()
    assert data["total_images"] == 665
    assert data["total_defects"] == 1739
    assert "pothole" in data["class_distribution"]
    assert "chitholian/annotated-potholes-dataset" in data["dataset_name"]


def test_dataset_stats(client):
    assert "total_boxes" in client.get("/api/dataset-stats").json()


# ── Map ─────────────────────────────────────────────────────────────────────

def test_gis_data_has_no_demo_fallback(client):
    """The map must only ever show real logged findings."""
    settings.DB_PATH = settings.DB_PATH  # explicit: isolated db, nothing logged yet
    points = client.get("/api/gis-data").json()
    assert isinstance(points, list)
    for point in points:
        assert db.get_inspection(point["id"]) is not None


# ── Reference data ──────────────────────────────────────────────────────────

def test_portals_and_stages(client):
    portals = client.get("/api/civic/portals").json()
    assert any(p["code"] == "MCGM" for p in portals)
    assert all(p["simulated"] is True for p in portals)

    stages = client.get("/api/civic/stages").json()
    assert [s["key"] for s in stages] == civic.STAGE_KEYS


def test_contractors_seeded(client):
    contractors = client.get("/api/contractors").json()
    assert len(contractors) >= 5
    assert all(c["rating"] > 0 and c["crew_count"] > 0 for c in contractors)


# ── Findings ────────────────────────────────────────────────────────────────

def test_log_finding_is_triaged_and_classified(client):
    res = client.post("/api/inspections", json=_finding_payload())
    assert res.status_code == 200
    finding = res.json()
    assert finding["id"] > 0
    # secondary OSM road -> Collector; severe + 4 defects -> high priority
    assert finding["road_class"] == "Collector"
    assert finding["priority"] in ("P1", "P2")
    assert finding["priority_score"] > 50
    assert finding["patch_area_m2"] == pytest.approx(4 * 1.20)
    assert finding["case_id"] is None

    assert any(f["id"] == finding["id"] for f in client.get("/api/inspections").json())
    points = client.get("/api/gis-data").json()
    point = next(p for p in points if p["id"] == finding["id"])
    assert point["case_status"] == "UNFILED"
    assert point["repaired"] is False


def test_log_finding_rejects_out_of_range_coordinates(client):
    res = client.post("/api/inspections", json=_finding_payload(lat=120.0))
    assert res.status_code == 422


# ── Full pipeline ───────────────────────────────────────────────────────────

def test_case_pipeline_end_to_end(client):
    finding = client.post("/api/inspections", json=_finding_payload()).json()

    # 1. Bundle into a triaged, costed case
    case = client.post("/api/civic/cases", json={"inspection_ids": [finding["id"]]}).json()
    case_id = case["id"]
    assert case["status"] == "DRAFT"
    assert case["total_potholes"] == 4
    assert case["estimate_inr"] > 0
    assert case["boq"]["total_inr"] == case["estimate_inr"]
    assert case["boq"]["gst_inr"] > 0
    assert case["portal"] is None
    assert case["sla_state"] == "NOT_STARTED"
    assert len(case["events"]) >= 1
    assert client.get(f"/api/inspections").json()[0]["case_id"] in (case_id, None)

    # An empty bundle is a client error, not a crash
    assert client.post("/api/civic/cases", json={"inspection_ids": []}).status_code == 422
    assert client.post("/api/civic/cases", json={"inspection_ids": [99999]}).status_code == 400

    # 2. File it — routed to MCGM by coordinate
    submitted = client.post(f"/api/civic/cases/{case_id}/submit").json()
    assert submitted["status"] == "SUBMITTED"
    assert submitted["portal"]["code"] == "MCGM"
    assert submitted["tracking_id"].startswith("MCGM/RTD/")
    assert "Brihanmumbai" in submitted["routing_note"]

    # 3. The portal acknowledges on its own — no button involved
    acked = _await_stage(client, case_id, "ACKNOWLEDGED")
    assert acked["officer"]
    assert acked["sla_due_at"] is not None
    assert acked["sla_state"] in ("ON_TRACK", "AT_RISK", "BREACHED")

    # 4. Tender, then award the lowest bid
    tendered = client.post(f"/api/civic/cases/{case_id}/tender").json()
    assert tendered["status"] == "TENDERED"
    assert len(tendered["bids"]) >= 5
    quotes = [b["quoted_inr"] for b in tendered["bids"]]
    assert quotes == sorted(quotes)

    assert client.post(f"/api/civic/cases/{case_id}/award", json={"contractor_id": 9999}).status_code == 400

    winner = tendered["bids"][0]
    awarded = client.post(
        f"/api/civic/cases/{case_id}/award", json={"contractor_id": winner["contractor_id"]}
    ).json()
    assert awarded["status"] == "WORK_ORDERED"
    assert awarded["awarded"]["contractor_id"] == winner["contractor_id"]
    assert awarded["awarded"]["awarded_inr"] == winner["quoted_inr"]

    # 5. The crew mobilises and finishes on the simulated clock
    repairing = _await_stage(client, case_id, "IN_REPAIR")
    assert repairing["repair_progress_pct"] >= 0.0
    repaired = _await_stage(client, case_id, "REPAIRED")
    assert repaired["repair_progress_pct"] == 100.0
    assert repaired["repaired_at"] is not None

    # No certificate before verification
    assert client.get(f"/api/civic/cases/{case_id}/certificate.pdf").status_code == 409

    # 6. Re-inspection with an after-photo decides pass/fail
    sample_name = client.get("/api/samples").json()["samples"][0]
    sample_bytes = client.get(f"/api/sample/{sample_name}").content
    verified = client.post(
        f"/api/civic/cases/{case_id}/verify",
        files={"file": ("after.jpg", sample_bytes, "image/jpeg")},
    ).json()
    assert verified["verification"] is not None
    assert verified["verification"]["defects_before"] == 4
    # A real road photo still has potholes, so this is rework, not a pass.
    assert verified["status"] in ("VERIFIED", "IN_REPAIR")

    if verified["status"] == "IN_REPAIR":
        assert verified["verification"]["passed"] is False
        assert any("FAILED" in e["title"] for e in verified["events"])
        _await_stage(client, case_id, "REPAIRED")
        # A clean after-photo (no detections) passes. Use a blank frame.
        from io import BytesIO

        from PIL import Image

        blank = BytesIO()
        Image.new("RGB", (640, 480), (90, 90, 90)).save(blank, format="JPEG")
        verified = client.post(
            f"/api/civic/cases/{case_id}/verify",
            files={"file": ("after_clean.jpg", blank.getvalue(), "image/jpeg")},
        ).json()

    assert verified["status"] == "VERIFIED", verified["verification"]
    assert verified["verification"]["passed"] is True
    assert verified["verification"]["effectiveness_pct"] > 0

    # 7. Close the case
    closed = client.post(f"/api/civic/cases/{case_id}/close").json()
    assert closed["status"] == "CLOSED"
    assert closed["closed_at"] is not None
    assert closed["sla_state"] in ("MET", "BREACHED")

    # The audit trail covers every stage the case actually passed through
    stages_logged = {e["stage"] for e in closed["events"]}
    assert {"DRAFT", "SUBMITTED", "ACKNOWLEDGED", "TENDERED", "WORK_ORDERED", "REPAIRED", "VERIFIED", "CLOSED"} <= stages_logged

    # The map now reports the finding as repaired
    point = next(p for p in client.get("/api/gis-data").json() if p["id"] == finding["id"])
    assert point["case_status"] == "CLOSED"
    assert point["repaired"] is True


def test_deliverables(client):
    finding = client.post("/api/inspections", json=_finding_payload(road_name="MG Road")).json()
    case_id = client.post("/api/civic/cases", json={"inspection_ids": [finding["id"]]}).json()["id"]

    dossier = client.get(f"/api/civic/cases/{case_id}/dossier.pdf")
    assert dossier.status_code == 200
    assert dossier.headers["content-type"] == "application/pdf"
    assert dossier.content.startswith(b"%PDF")

    payload = client.get(f"/api/civic/cases/{case_id}/export.json")
    assert payload.status_code == 200
    body = payload.json()
    assert body["schema"] == "crackmap.civic.case/1"
    assert body["filing_is_simulated"] is True
    assert body["case"]["id"] == case_id

    inventory = client.get(f"/api/civic/cases/{case_id}/export.csv")
    assert inventory.status_code == 200
    assert inventory.headers["content-type"].startswith("text/csv")
    rows = inventory.text.strip().splitlines()
    assert rows[0].startswith("case_id,tracking_id,case_status")
    assert len(rows) == 1 + finding["total_defects"]

    assert client.get("/api/civic/cases/999999/dossier.pdf").status_code == 404


def test_stats_and_events(client):
    stats = client.get("/api/civic/stats").json()
    assert stats["total_cases"] >= 1
    assert stats["total_findings"] >= 1
    assert set(stats["stage_counts"]) == set(civic.STAGE_KEYS)
    assert stats["potholes_reported"] >= stats["potholes_repaired"]
    assert stats["seconds_per_sim_day"] == settings.SIM_SECONDS_PER_DAY

    events = client.get("/api/civic/events?limit=10").json()
    assert 0 < len(events) <= 10
    assert all(e["actor"] and e["title"] for e in events)


def test_stage_actions_are_order_safe(client):
    """Actions fired out of order are no-ops, never corruption."""
    finding = client.post("/api/inspections", json=_finding_payload()).json()
    case_id = client.post("/api/civic/cases", json={"inspection_ids": [finding["id"]]}).json()["id"]

    # Tender/award/close before filing: the case stays a draft.
    assert client.post(f"/api/civic/cases/{case_id}/tender").json()["status"] == "DRAFT"
    assert client.post(f"/api/civic/cases/{case_id}/close").json()["status"] == "DRAFT"

    client.post(f"/api/civic/cases/{case_id}/submit")
    # Submitting twice does not re-file or mint a second grievance number.
    first = client.get(f"/api/civic/cases/{case_id}").json()["tracking_id"]
    assert client.post(f"/api/civic/cases/{case_id}/submit").json()["tracking_id"] == first

    assert client.post("/api/civic/cases/999999/submit").status_code == 404
    assert client.get("/api/civic/cases/999999").status_code == 404


def test_training_endpoints(client):
    assert client.get("/api/train-status").json()["status"] == "idle"
    res = client.post(
        "/api/train-model",
        data={"epochs": "5", "batch_size": "4", "learning_rate": "0.005", "architecture": "fasterrcnn_mobilenet"},
    )
    assert res.json()["success"] is True


# ── SLA semantics ───────────────────────────────────────────────────────────

def test_sla_is_a_response_deadline_not_a_completion_deadline():
    """A prompt work order must stay compliant however long the asphalt takes.

    Municipal road cells commit to *responding* within the published window, so
    a slow repair after a fast response is not a breach.
    """
    spd = 12.0
    acknowledged_at = 1000.0
    due_at = civic.sla_deadline(acknowledged_at, 24.0, spd)
    assert due_at == 1012.0

    # Work order issued 6s (12 simulated hours) in, repair drags on for ages.
    prompt = civic.sla_status(due_at, acknowledged_at + 6.0, 999_999.0, spd)
    assert prompt["sla_state"] == "MET"
    assert prompt["breached"] is False
    assert prompt["hours_remaining"] == 12.0

    # Work order issued after the window closed: that is the breach.
    late = civic.sla_status(due_at, acknowledged_at + 30.0, 999_999.0, spd)
    assert late["sla_state"] == "BREACHED"
    assert late["breached"] is True
    assert late["hours_remaining"] < 0

    # Still unawarded: the clock runs against now.
    assert civic.sla_status(due_at, None, 1006.0, spd)["sla_state"] in ("ON_TRACK", "AT_RISK")
    assert civic.sla_status(due_at, None, 1030.0, spd)["breached"] is True
    assert civic.sla_status(None, None, 1000.0, spd)["sla_state"] == "NOT_STARTED"
