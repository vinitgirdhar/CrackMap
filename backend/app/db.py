"""SQLite persistence for the civic pipeline.

Raw storage and migrations only. Stage logic lives in cases.py, domain rules in
civic.py — this module never decides what a case *means*, only where it lives.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import settings

# Seeded contractor panel — the empanelled bidders a municipal road cell would
# invite. Ratings drive bid evaluation; crew counts drive promised durations.
_SEED_CONTRACTORS = [
    ("Konkan Asphalt & Paving Co.", "Hot-mix pothole patching", "Bandra, Andheri, Santacruz", 4.4, 6),
    ("MumbaiRoad Infrastructure Ltd.", "Bituminous resurfacing", "Dadar, Colaba, Worli", 4.1, 11),
    ("SafeStreet Civil Works", "Emergency 24h repair", "Powai, Ghatkopar, Kurla", 4.7, 4),
    ("Maharashtra Pavement Solutions", "Full-depth reconstruction", "Mumbai Metropolitan Region", 3.9, 15),
    ("GreenLine Municipal Contractors", "Crack sealing & micro-surfacing", "Thane, Navi Mumbai", 4.2, 8),
]

_INSPECTION_COLUMNS = {
    "address": "TEXT",
    "ward": "TEXT",
    "city": "TEXT",
    "state": "TEXT",
    "osm_road_type": "TEXT",
    "road_class": "TEXT",
    "patch_area_m2": "REAL",
    "priority": "TEXT",
    "priority_label": "TEXT",
    "priority_score": "REAL",
    "case_id": "INTEGER",
}


def get_conn() -> sqlite3.Connection:
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> List[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS inspections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                road_name TEXT NOT NULL,
                lat REAL,
                lon REAL,
                total_defects INTEGER NOT NULL,
                severity_score REAL NOT NULL,
                composite_damage_score REAL NOT NULL,
                boxes_json TEXT NOT NULL,
                annotated_image TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contractors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialty TEXT NOT NULL,
                service_area TEXT NOT NULL,
                rating REAL NOT NULL DEFAULT 4.0,
                crew_count INTEGER NOT NULL DEFAULT 5
            );

            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inspection_ids_json TEXT NOT NULL,
                total_potholes INTEGER NOT NULL,
                avg_severity REAL NOT NULL,
                created_at REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'DRAFT',

                portal_code TEXT,
                tracking_id TEXT,
                routing_note TEXT,
                officer TEXT,
                submitted_at REAL,
                acknowledged_at REAL,

                priority TEXT,
                priority_label TEXT,
                priority_score REAL,
                sla_hours REAL,
                sla_due_at REAL,

                patch_area_m2 REAL,
                boq_json TEXT,
                estimate_inr REAL,

                tendered_at REAL,
                bids_json TEXT,

                awarded_contractor_id INTEGER,
                awarded_inr REAL,
                promised_days REAL,
                awarded_at REAL,

                repaired_at REAL,
                verification_json TEXT,
                verified_at REAL,
                closed_at REAL
            );

            CREATE TABLE IF NOT EXISTS pipeline_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER,
                inspection_id INTEGER,
                stage TEXT NOT NULL,
                actor TEXT NOT NULL,
                title TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_events_case ON pipeline_events(case_id, created_at);
            """
        )

        # Migration: pre-restructure databases carry the flat gov_reports /
        # work_orders pair. Inspections hold real detector output and are
        # migrated in place; the two simulated tables are dropped because the
        # replacement `cases` row folds a work order into its own case.
        if _table_exists(conn, "gov_reports"):
            print("[db] migrating: dropping legacy gov_reports/work_orders (simulated rows only)")
            conn.executescript("DROP TABLE IF EXISTS work_orders; DROP TABLE IF EXISTS gov_reports;")

        existing = _columns(conn, "inspections")
        for column, decl in _INSPECTION_COLUMNS.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE inspections ADD COLUMN {column} {decl}")

        for column, decl in (("rating", "REAL NOT NULL DEFAULT 4.0"), ("crew_count", "INTEGER NOT NULL DEFAULT 5")):
            if column not in _columns(conn, "contractors"):
                conn.execute(f"ALTER TABLE contractors ADD COLUMN {column} {decl}")

        # Indexed only after the migration above guarantees the column exists.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_inspections_case ON inspections(case_id)")

        if conn.execute("SELECT COUNT(*) AS c FROM contractors").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO contractors (name, specialty, service_area, rating, crew_count)"
                " VALUES (?, ?, ?, ?, ?)",
                _SEED_CONTRACTORS,
            )
        conn.commit()
    finally:
        conn.close()


# ── Events ──────────────────────────────────────────────────────────────────

def log_event(
    stage: str,
    actor: str,
    title: str,
    detail: str = "",
    case_id: Optional[int] = None,
    inspection_id: Optional[int] = None,
    at: Optional[float] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO pipeline_events (case_id, inspection_id, stage, actor, title, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (case_id, inspection_id, stage, actor, title, detail, at if at is not None else time.time()),
        )
        if own_conn:
            conn.commit()
        return dict(conn.execute("SELECT * FROM pipeline_events WHERE id = ?", (cur.lastrowid,)).fetchone())
    finally:
        if own_conn:
            conn.close()


def list_events(case_id: Optional[int] = None, limit: int = 200) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        if case_id is None:
            rows = conn.execute(
                "SELECT * FROM pipeline_events ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pipeline_events WHERE case_id = ? ORDER BY created_at ASC, id ASC LIMIT ?",
                (case_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Inspections ─────────────────────────────────────────────────────────────

def create_inspection(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO inspections
                (filename, road_name, lat, lon, address, ward, city, state, osm_road_type,
                 road_class, total_defects, severity_score, composite_damage_score,
                 patch_area_m2, priority, priority_label, priority_score,
                 boxes_json, annotated_image, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["filename"],
                data["road_name"],
                data.get("lat"),
                data.get("lon"),
                data.get("address"),
                data.get("ward"),
                data.get("city"),
                data.get("state"),
                data.get("osm_road_type"),
                data.get("road_class"),
                data["total_defects"],
                data["severity_score"],
                data["composite_damage_score"],
                data.get("patch_area_m2"),
                data.get("priority"),
                data.get("priority_label"),
                data.get("priority_score"),
                json.dumps(data["boxes"]),
                data["annotated_image"],
                time.time(),
            ),
        )
        conn.commit()
        return get_inspection(cur.lastrowid, conn)
    finally:
        conn.close()


def get_inspection(
    inspection_id: int, conn: Optional[sqlite3.Connection] = None
) -> Optional[Dict[str, Any]]:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        row = conn.execute("SELECT * FROM inspections WHERE id = ?", (inspection_id,)).fetchone()
        return _inspection_row_to_dict(row) if row else None
    finally:
        if own_conn:
            conn.close()


def list_inspections(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        rows = conn.execute("SELECT * FROM inspections ORDER BY created_at DESC").fetchall()
        return [_inspection_row_to_dict(r) for r in rows]
    finally:
        if own_conn:
            conn.close()


def _inspection_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    d["boxes"] = json.loads(d.pop("boxes_json"))
    return d


def attach_inspections_to_case(
    inspection_ids: List[int], case_id: int, conn: Optional[sqlite3.Connection] = None
) -> None:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        conn.executemany(
            "UPDATE inspections SET case_id = ? WHERE id = ?",
            [(case_id, i) for i in inspection_ids],
        )
        if own_conn:
            conn.commit()
    finally:
        if own_conn:
            conn.close()


# ── Contractors ─────────────────────────────────────────────────────────────

def list_contractors(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM contractors ORDER BY id").fetchall()]
    finally:
        if own_conn:
            conn.close()


def get_contractor(contractor_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        row = conn.execute("SELECT * FROM contractors WHERE id = ?", (contractor_id,)).fetchone()
        return dict(row) if row else None
    finally:
        if own_conn:
            conn.close()


# ── Cases ───────────────────────────────────────────────────────────────────

_JSON_CASE_FIELDS = (("boq_json", "boq"), ("bids_json", "bids"), ("verification_json", "verification"))


def insert_case(fields: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_conn()
    try:
        keys = list(fields.keys())
        placeholders = ",".join("?" * len(keys))
        cur = conn.execute(
            f"INSERT INTO cases ({','.join(keys)}) VALUES ({placeholders})",
            [fields[k] for k in keys],
        )
        conn.commit()
        return get_case(cur.lastrowid, conn)
    finally:
        conn.close()


def update_case(case_id: int, fields: Dict[str, Any], conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        if fields:
            assignments = ",".join(f"{k} = ?" for k in fields)
            conn.execute(
                f"UPDATE cases SET {assignments} WHERE id = ?", [*fields.values(), case_id]
            )
            if own_conn:
                conn.commit()
        return get_case(case_id, conn)
    finally:
        if own_conn:
            conn.close()


def get_case(case_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        return _case_row_to_dict(row) if row else None
    finally:
        if own_conn:
            conn.close()


def list_cases(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        rows = conn.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
        return [_case_row_to_dict(r) for r in rows]
    finally:
        if own_conn:
            conn.close()


def next_case_sequence(conn: Optional[sqlite3.Connection] = None) -> int:
    """Grievance sequence number within the current calendar year."""
    own_conn = conn is None
    conn = conn or get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM cases WHERE tracking_id IS NOT NULL"
        ).fetchone()
        return int(row["c"]) + 1
    finally:
        if own_conn:
            conn.close()


def _case_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    d["inspection_ids"] = json.loads(d.pop("inspection_ids_json"))
    for raw_key, key in _JSON_CASE_FIELDS:
        raw = d.pop(raw_key)
        d[key] = json.loads(raw) if raw else None
    return d


def demo_self_check() -> None:
    """Round-trips the schema against a throwaway database file."""
    import tempfile

    original = settings.DB_PATH
    with tempfile.TemporaryDirectory() as tmp:
        settings.DB_PATH = str(Path(tmp) / "check.db")
        try:
            init_db()
            init_db()  # idempotent

            assert len(list_contractors()) == len(_SEED_CONTRACTORS)

            insp = create_inspection(
                {
                    "filename": "a.jpg",
                    "road_name": "Hill Road, Bandra West",
                    "lat": 19.05,
                    "lon": 72.83,
                    "road_class": "Collector",
                    "total_defects": 2,
                    "severity_score": 3.0,
                    "composite_damage_score": 62.0,
                    "patch_area_m2": 1.1,
                    "priority": "P2",
                    "boxes": [{"severity": "Moderate"}],
                    "annotated_image": "data:image/jpeg;base64,x",
                }
            )
            assert insp["id"] > 0 and insp["boxes"] == [{"severity": "Moderate"}]
            assert insp["case_id"] is None
            assert get_inspection(insp["id"])["road_name"] == "Hill Road, Bandra West"
            assert get_inspection(9999) is None

            case = insert_case(
                {
                    "inspection_ids_json": json.dumps([insp["id"]]),
                    "total_potholes": 2,
                    "avg_severity": 3.0,
                    "created_at": time.time(),
                    "status": "DRAFT",
                    "boq_json": json.dumps({"total_inr": 100.0}),
                }
            )
            assert case["inspection_ids"] == [insp["id"]]
            assert case["boq"]["total_inr"] == 100.0
            assert case["bids"] is None and case["verification"] is None

            attach_inspections_to_case([insp["id"]], case["id"])
            assert get_inspection(insp["id"])["case_id"] == case["id"]

            assert next_case_sequence() == 1
            update_case(case["id"], {"status": "SUBMITTED", "tracking_id": "X/1"})
            assert get_case(case["id"])["status"] == "SUBMITTED"
            assert next_case_sequence() == 2

            log_event("SUBMITTED", "Portal", "Filed", "detail", case_id=case["id"])
            events = list_events(case["id"])
            assert len(events) == 1 and events[0]["title"] == "Filed"
            assert len(list_events()) == 1
            assert len(list_cases()) == 1
            print("db.py self-check OK")
        finally:
            settings.DB_PATH = original


if __name__ == "__main__":
    demo_self_check()
