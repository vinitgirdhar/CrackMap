"""Civic case orchestration: the stage machine and the denormalised read model.

A *case* is one municipal grievance: a bundle of inspected findings, the portal
it was filed with, the tender that priced it, the contract that repaired it and
the re-inspection that proved it. Stages advance two ways:

  * explicit acts a human performs (file, tender, award, verify, close), and
  * the passage of time (portal acknowledgement, crew mobilisation, repair
    progress), which `reconcile` persists on read.

Reconciliation on read is what makes the pipeline move on its own instead of
waiting for a Next button.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import civic, db
from .config import settings


def seconds_per_day() -> float:
    return settings.SIM_SECONDS_PER_DAY


# ── Creation ────────────────────────────────────────────────────────────────

def create_case(inspection_ids: List[int]) -> Dict[str, Any]:
    """Bundle logged findings into a triaged, costed draft grievance."""
    findings = [db.get_inspection(i) for i in inspection_ids]
    findings = [f for f in findings if f is not None]
    if not findings:
        raise ValueError("None of the supplied inspection ids exist")

    total_potholes = sum(f["total_defects"] for f in findings)
    avg_severity = round(sum(f["severity_score"] for f in findings) / len(findings), 2)
    total_area = round(sum(f.get("patch_area_m2") or civic.patch_area_m2(f["boxes"]) for f in findings), 2)

    # The case inherits the worst road class among its findings — a bundle that
    # touches an arterial road is triaged as an arterial job.
    road_class = max(
        (f.get("road_class") or "Local" for f in findings),
        key=lambda rc: civic.ROAD_CLASS_WEIGHT.get(rc, 0.45),
    )
    triage = civic.assess_priority(avg_severity, total_potholes, road_class)
    boq = civic.build_boq(total_area)

    case = db.insert_case(
        {
            "inspection_ids_json": json.dumps([f["id"] for f in findings]),
            "total_potholes": total_potholes,
            "avg_severity": avg_severity,
            "created_at": time.time(),
            "status": "DRAFT",
            "priority": triage["priority"],
            "priority_label": triage["priority_label"],
            "priority_score": triage["priority_score"],
            "sla_hours": triage["sla_hours"],
            "patch_area_m2": total_area,
            "boq_json": json.dumps(boq),
            "estimate_inr": boq["total_inr"],
        }
    )
    db.attach_inspections_to_case([f["id"] for f in findings], case["id"])
    db.log_event(
        "DRAFT",
        "CrackMap Triage Engine",
        f"Case #{case['id']} opened — {triage['priority']} {triage['priority_label']}",
        f"{len(findings)} finding(s), {total_potholes} pothole(s) across {total_area} m². "
        f"Engineer's estimate ₹{boq['total_inr']:,.0f}. Response window {triage['sla_hours']:.0f}h.",
        case_id=case["id"],
        at=case["created_at"],
    )
    return case


# ── Explicit stage actions ──────────────────────────────────────────────────

def submit_case(case_id: int) -> Optional[Dict[str, Any]]:
    """File the case with the municipal portal that owns its coordinates."""
    case = db.get_case(case_id)
    if case is None:
        return None
    if case["status"] != "DRAFT":
        return case

    findings = _findings_for(case)
    located = next((f for f in findings if f["lat"] is not None), None)
    portal, routing_note = civic.route_to_portal(
        located["lat"] if located else None, located["lon"] if located else None
    )
    now = time.time()
    tracking_id = civic.format_tracking_id(
        portal, datetime.fromtimestamp(now).year, db.next_case_sequence()
    )

    updated = db.update_case(
        case_id,
        {
            "status": "SUBMITTED",
            "portal_code": portal["code"],
            "tracking_id": tracking_id,
            "routing_note": routing_note,
            "submitted_at": now,
        },
    )
    db.log_event(
        "SUBMITTED",
        "CrackMap Filing Agent",
        f"Filed with {portal['authority']} — {tracking_id}",
        f"Submitted to {portal['name']} ({portal['department']}). {routing_note} "
        f"Awaiting portal acknowledgement.",
        case_id=case_id,
        at=now,
    )
    return updated


def tender_case(case_id: int) -> Optional[Dict[str, Any]]:
    """Invite the empanelled contractor panel to quote against the BOQ."""
    case = db.get_case(case_id)
    if case is None:
        return None
    case = reconcile(case)
    if case["status"] != "ACKNOWLEDGED":
        return case

    contractors = db.list_contractors()
    duration = civic.repair_duration_days(case["patch_area_m2"] or 0.0)
    bids = civic.generate_bids(case_id, contractors, case["estimate_inr"] or 0.0, duration)
    now = time.time()

    updated = db.update_case(
        case_id, {"status": "TENDERED", "tendered_at": now, "bids_json": json.dumps(bids)}
    )
    db.log_event(
        "TENDERED",
        civic.get_portal(case["portal_code"] or "")["department"],
        f"Tender floated to {len(bids)} empanelled contractors",
        f"Lowest quote ₹{bids[0]['quoted_inr']:,.0f} from {bids[0]['contractor_name']} "
        f"({bids[0]['variance_pct']:+.1f}% vs estimate).",
        case_id=case_id,
        at=now,
    )
    return updated


def award_case(case_id: int, contractor_id: int) -> Optional[Dict[str, Any]]:
    """Award the work order to one bidder and issue the contract."""
    case = db.get_case(case_id)
    if case is None:
        return None
    case = reconcile(case)
    if case["status"] != "TENDERED":
        return case

    bid = next((b for b in (case["bids"] or []) if b["contractor_id"] == contractor_id), None)
    if bid is None:
        raise ValueError(f"Contractor {contractor_id} did not bid on case {case_id}")

    now = time.time()
    updated = db.update_case(
        case_id,
        {
            "status": "WORK_ORDERED",
            "awarded_contractor_id": contractor_id,
            "awarded_inr": bid["quoted_inr"],
            "promised_days": bid["promised_days"],
            "awarded_at": now,
        },
    )
    db.log_event(
        "WORK_ORDERED",
        civic.get_portal(case["portal_code"] or "")["department"],
        f"Work order issued to {bid['contractor_name']}",
        f"Contract value ₹{bid['quoted_inr']:,.0f} against an estimate of "
        f"₹{case['estimate_inr']:,.0f}. Completion promised in {bid['promised_days']:.0f} day(s).",
        case_id=case_id,
        at=now,
    )
    return updated


def verify_case(case_id: int, after_detection: Dict[str, Any], filename: str) -> Optional[Dict[str, Any]]:
    """Re-inspect the repaired road with the same detector and judge the work.

    A repair passes when the after-photo shows at most `VERIFICATION_PASS_RATIO`
    of the originally detected defects. A failure sends the case back into
    repair as rework, which is what a municipal engineer would actually do.
    """
    case = db.get_case(case_id)
    if case is None:
        return None
    case = reconcile(case)
    if case["status"] not in ("REPAIRED", "IN_REPAIR"):
        return case

    before = case["total_potholes"]
    after = int(after_detection["total_defects"])
    ratio = after / max(1, before)
    passed = ratio <= civic.VERIFICATION_PASS_RATIO
    now = time.time()

    verification = {
        "filename": filename,
        "defects_before": before,
        "defects_after": after,
        "remaining_ratio": round(ratio, 3),
        "effectiveness_pct": round(max(0.0, (1.0 - ratio)) * 100.0, 1),
        "severity_after": after_detection.get("severity_score", 0.0),
        "damage_score_after": after_detection.get("composite_damage_score", 0.0),
        "annotated_image": after_detection.get("annotated_image", ""),
        "passed": passed,
        "checked_at": now,
        "attempts": ((case["verification"] or {}).get("attempts") or 0) + 1,
    }

    if passed:
        updated = db.update_case(
            case_id,
            {
                "status": "VERIFIED",
                "verification_json": json.dumps(verification),
                "verified_at": now,
            },
        )
        db.log_event(
            "VERIFIED",
            "CrackMap AI Re-Inspection",
            f"Re-inspection passed — {verification['effectiveness_pct']:.0f}% of defects cleared",
            f"{before} pothole(s) before, {after} detected after repair. "
            f"Post-repair damage score {verification['damage_score_after']}/100.",
            case_id=case_id,
            at=now,
        )
        return updated

    updated = db.update_case(
        case_id,
        {
            "status": "IN_REPAIR",
            "verification_json": json.dumps(verification),
            "repaired_at": None,
            # Restart the repair clock so the rework visibly runs again.
            "awarded_at": now,
        },
    )
    db.log_event(
        "IN_REPAIR",
        "CrackMap AI Re-Inspection",
        f"Re-inspection FAILED — {after} of {before} defect(s) still present",
        "Only "
        f"{verification['effectiveness_pct']:.0f}% of defects were cleared, below the "
        f"{civic.VERIFICATION_PASS_RATIO * 100:.0f}% remaining-defect threshold. "
        "Case returned to the contractor as rework.",
        case_id=case_id,
        at=now,
    )
    return updated


def close_case(case_id: int) -> Optional[Dict[str, Any]]:
    """Close a verified case and release the completion certificate."""
    case = db.get_case(case_id)
    if case is None:
        return None
    case = reconcile(case)
    if case["status"] != "VERIFIED":
        return case

    now = time.time()
    updated = db.update_case(case_id, {"status": "CLOSED", "closed_at": now})
    sla = civic.sla_status(case["sla_due_at"], case["awarded_at"], now, seconds_per_day())
    db.log_event(
        "CLOSED",
        civic.get_portal(case["portal_code"] or "")["department"],
        f"Case closed — grievance {case['tracking_id']} resolved",
        f"Completion certificate issued. Statutory window {sla['sla_state']}. "
        f"Final contract value ₹{(case['awarded_inr'] or 0):,.0f}.",
        case_id=case_id,
        at=now,
    )
    return updated


# ── Time-driven reconciliation ──────────────────────────────────────────────

def reconcile(case: Dict[str, Any], now: Optional[float] = None) -> Dict[str, Any]:
    """Advance the stages the clock owns, persisting each with an audit event.

    Idempotent: calling it repeatedly only ever moves a case forward, and only
    once per transition.
    """
    now = now if now is not None else time.time()
    spd = seconds_per_day()

    if case["status"] == "SUBMITTED":
        ack_at = case["submitted_at"] + civic.sim_day_to_real_seconds(civic.ACK_LAG_DAYS, spd)
        if now >= ack_at:
            portal = civic.get_portal(case["portal_code"] or "")
            officer = civic.pick_officer(portal, f"case-{case['id']}")
            due_at = civic.sla_deadline(ack_at, case["sla_hours"] or 720.0, spd)
            case = db.update_case(
                case["id"],
                {
                    "status": "ACKNOWLEDGED",
                    "acknowledged_at": ack_at,
                    "officer": officer,
                    "sla_due_at": due_at,
                },
            )
            db.log_event(
                "ACKNOWLEDGED",
                portal["name"],
                f"Grievance acknowledged — assigned to {officer}",
                f"{portal['authority']} accepted {case['tracking_id']} and committed to a "
                f"{case['sla_hours']:.0f}-hour response window for a "
                f"{case['priority']} complaint.",
                case_id=case["id"],
                at=ack_at,
            )

    if case["status"] == "WORK_ORDERED":
        progress = civic.repair_progress(case["awarded_at"], case["promised_days"] or 1.0, now, spd)
        if progress["mobilised"]:
            contractor = db.get_contractor(case["awarded_contractor_id"] or 0) or {"name": "Contractor", "crew_count": 4}
            mobilised_at = case["awarded_at"] + civic.sim_day_to_real_seconds(civic.MOBILISATION_LAG_DAYS, spd)
            case = db.update_case(case["id"], {"status": "IN_REPAIR"})
            db.log_event(
                "IN_REPAIR",
                contractor["name"],
                "Crew mobilised on site — repair started",
                f"{contractor.get('crew_count', 4)}-person crew began hot-mix patching of "
                f"{case['patch_area_m2']} m² across {case['total_potholes']} pothole(s).",
                case_id=case["id"],
                at=mobilised_at,
            )

    if case["status"] == "IN_REPAIR":
        progress = civic.repair_progress(case["awarded_at"], case["promised_days"] or 1.0, now, spd)
        if progress["complete"]:
            contractor = db.get_contractor(case["awarded_contractor_id"] or 0) or {"name": "Contractor"}
            done_at = case["awarded_at"] + civic.sim_day_to_real_seconds(
                civic.MOBILISATION_LAG_DAYS + (case["promised_days"] or 1.0), spd
            )
            case = db.update_case(case["id"], {"status": "REPAIRED", "repaired_at": done_at})
            db.log_event(
                "REPAIRED",
                contractor["name"],
                "Contractor reported completion — awaiting re-inspection",
                "Patching, compaction and edge sealing complete. Upload an after-photo to "
                "run an AI re-inspection before the case can be closed.",
                case_id=case["id"],
                at=done_at,
            )

    return case


def reconcile_all() -> List[Dict[str, Any]]:
    return [reconcile(case) for case in db.list_cases()]


# ── Read model ──────────────────────────────────────────────────────────────

def _findings_for(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings = [db.get_inspection(i) for i in case["inspection_ids"]]
    return [f for f in findings if f is not None]


def assemble(case: Dict[str, Any], include_images: bool = False) -> Dict[str, Any]:
    """One self-contained case object: everything the UI renders in one fetch."""
    now = time.time()
    spd = seconds_per_day()
    findings = _findings_for(case)
    progress = civic.repair_progress(case["awarded_at"], case["promised_days"] or 1.0, now, spd)
    # Responded == work order issued; see civic.sla_status.
    sla = civic.sla_status(case["sla_due_at"], case["awarded_at"], now, spd)
    severity_label, severity_hex, _ = civic.severity_band(case["avg_severity"])

    awarded = None
    if case["awarded_contractor_id"]:
        contractor = db.get_contractor(case["awarded_contractor_id"])
        bid = next(
            (b for b in (case["bids"] or []) if b["contractor_id"] == case["awarded_contractor_id"]),
            None,
        )
        awarded = {
            "contractor_id": case["awarded_contractor_id"],
            "contractor_name": (contractor or {}).get("name", "Unknown contractor"),
            "specialty": (contractor or {}).get("specialty", ""),
            "rating": (contractor or {}).get("rating", 0.0),
            "crew_count": (contractor or {}).get("crew_count", 0),
            "awarded_inr": case["awarded_inr"],
            "promised_days": case["promised_days"],
            "variance_pct": (bid or {}).get("variance_pct", 0.0),
            "awarded_at": case["awarded_at"],
        }

    return {
        "id": case["id"],
        "status": case["status"],
        "stage_index": civic.stage_index(case["status"]),
        "stage_label": civic.STAGES[civic.stage_index(case["status"])]["label"],
        "created_at": case["created_at"],
        "total_potholes": case["total_potholes"],
        "avg_severity": case["avg_severity"],
        "severity_label": severity_label,
        "severity_hex": severity_hex,
        "priority": case["priority"],
        "priority_label": case["priority_label"],
        "priority_score": case["priority_score"],
        "patch_area_m2": case["patch_area_m2"],
        "estimate_inr": case["estimate_inr"],
        "boq": case["boq"],
        "portal": _portal_view(case),
        "tracking_id": case["tracking_id"],
        "routing_note": case["routing_note"],
        "officer": case["officer"],
        "submitted_at": case["submitted_at"],
        "acknowledged_at": case["acknowledged_at"],
        "sla_hours": case["sla_hours"],
        "sla_due_at": case["sla_due_at"],
        **sla,
        "tendered_at": case["tendered_at"],
        "bids": case["bids"] or [],
        "awarded": awarded,
        "repair_progress_pct": progress["progress_pct"] if case["awarded_at"] else 0.0,
        "repair_sim_days": progress["sim_days_elapsed"] if case["awarded_at"] else 0.0,
        "repaired_at": case["repaired_at"],
        "verification": case["verification"],
        "verified_at": case["verified_at"],
        "closed_at": case["closed_at"],
        "seconds_per_sim_day": spd,
        "findings": [_finding_view(f, include_images) for f in findings],
        "events": db.list_events(case["id"]),
    }


def _finding_view(finding: Dict[str, Any], include_images: bool) -> Dict[str, Any]:
    view = {
        "id": finding["id"],
        "filename": finding["filename"],
        "road_name": finding["road_name"],
        "address": finding.get("address"),
        "ward": finding.get("ward"),
        "city": finding.get("city"),
        "road_class": finding.get("road_class") or "Local",
        "lat": finding["lat"],
        "lon": finding["lon"],
        "total_defects": finding["total_defects"],
        "severity_score": finding["severity_score"],
        "composite_damage_score": finding["composite_damage_score"],
        "patch_area_m2": finding.get("patch_area_m2"),
        "priority": finding.get("priority"),
        "created_at": finding["created_at"],
        "case_id": finding.get("case_id"),
        "boxes": finding["boxes"],
    }
    view["annotated_image"] = finding["annotated_image"] if include_images else ""
    return view


def list_case_views(include_images: bool = False) -> List[Dict[str, Any]]:
    reconcile_all()
    return [assemble(case, include_images) for case in db.list_cases()]


def get_case_view(case_id: int, include_images: bool = True) -> Optional[Dict[str, Any]]:
    case = db.get_case(case_id)
    if case is None:
        return None
    return assemble(reconcile(case), include_images)


def pipeline_stats() -> Dict[str, Any]:
    """Board-level counters: where cases sit, what is at risk, what it cost."""
    views = list_case_views(include_images=False)
    findings = db.list_inspections()

    stage_counts = {stage["key"]: 0 for stage in civic.STAGES}
    for view in views:
        stage_counts[view["status"]] = stage_counts.get(view["status"], 0) + 1

    closed = [v for v in views if v["status"] == "CLOSED"]
    committed = [v for v in views if v["awarded"]]
    return {
        "total_findings": len(findings),
        "unassigned_findings": len([f for f in findings if f.get("case_id") is None]),
        "total_cases": len(views),
        "stage_counts": stage_counts,
        "open_cases": len([v for v in views if v["status"] != "CLOSED"]),
        "closed_cases": len(closed),
        "sla_breached": len([v for v in views if v["breached"]]),
        "sla_at_risk": len([v for v in views if v["sla_state"] == "AT_RISK"]),
        "potholes_reported": sum(v["total_potholes"] for v in views),
        "potholes_repaired": sum(v["total_potholes"] for v in views if v["status"] in ("VERIFIED", "CLOSED")),
        "area_m2_reported": round(sum(v["patch_area_m2"] or 0.0 for v in views), 2),
        "estimated_inr": round(sum(v["estimate_inr"] or 0.0 for v in views), 2),
        "committed_inr": round(sum(v["awarded"]["awarded_inr"] or 0.0 for v in committed), 2),
        "seconds_per_sim_day": seconds_per_day(),
        "stages": civic.STAGES,
    }


def map_points() -> List[Dict[str, Any]]:
    """Every geolocated finding, carrying the live stage of its case."""
    reconcile_all()
    points = []
    for finding in db.list_inspections():
        if finding["lat"] is None or finding["lon"] is None:
            continue
        case = db.get_case(finding["case_id"]) if finding.get("case_id") else None
        severity_label, severity_hex, (r, g, b) = civic.severity_band(finding["severity_score"])
        boxes = finding["boxes"]
        avg_conf = (
            round(sum(box["confidence"] for box in boxes) / len(boxes) / 100.0, 2) if boxes else 0.0
        )
        repaired = case is not None and case["status"] in ("VERIFIED", "CLOSED")
        points.append(
            {
                "id": finding["id"],
                "road_name": finding["road_name"],
                "address": finding.get("address") or finding["road_name"],
                "ward": finding.get("ward") or "",
                "road_class": finding.get("road_class") or "Local",
                "lat": finding["lat"],
                "lon": finding["lon"],
                "total_defects": finding["total_defects"],
                "severity": severity_label,
                "severity_score": finding["severity_score"],
                "confidence": avg_conf,
                "damage_score": finding["composite_damage_score"],
                "priority": finding.get("priority") or "—",
                "color_hex": severity_hex,
                "color_r": r,
                "color_g": g,
                "color_b": b,
                "case_id": case["id"] if case else None,
                "case_status": case["status"] if case else "UNFILED",
                "tracking_id": case["tracking_id"] if case else None,
                "repaired": repaired,
                "logged_at": finding["created_at"],
            }
        )
    return points


# ── Completed-work records ──────────────────────────────────────────────────

COMPLETED_STATUSES = ("VERIFIED", "CLOSED")


def completed_records() -> List[Dict[str, Any]]:
    """Before/after record for every case whose repair has been verified.

    Carries the evidence images, so unlike the board list this is fetched only
    when the set of completed cases actually changes.
    """
    reconcile_all()
    records = []
    for case in db.list_cases():
        if case["status"] not in COMPLETED_STATUSES or not case["verification"]:
            continue
        records.append(_completed_record(case))
    return records


def _completed_record(case: Dict[str, Any]) -> Dict[str, Any]:
    spd = seconds_per_day()
    verification = case["verification"]
    findings = _findings_for(case)
    primary = next((f for f in findings if f["lat"] is not None), findings[0] if findings else None)
    roads = [f["road_name"] for f in findings] or ["Unrecorded location"]

    contractor = db.get_contractor(case["awarded_contractor_id"] or 0) or {}
    contractor_name = contractor.get("name", "Unrecorded contractor")
    specialty = contractor.get("specialty", "")
    crew_count = int(contractor.get("crew_count", 0))
    promised_days = float(case["promised_days"] or 0.0)
    awarded_inr = float(case["awarded_inr"] or 0.0)

    # What the job actually took, on the simulated clock the crew worked on.
    actual_days = (
        round(civic.sim_days_elapsed(case["awarded_at"], case["repaired_at"], spd), 2)
        if case["awarded_at"] and case["repaired_at"]
        else 0.0
    )
    end_at = case["closed_at"] or case["verified_at"]
    lifecycle_days = (
        round(civic.sim_days_elapsed(case["created_at"], end_at, spd), 2) if end_at else 0.0
    )

    road_class = (primary or {}).get("road_class") or "Local"
    boq = case["boq"] or civic.build_boq(case["patch_area_m2"] or 0.0)

    return {
        "case_id": case["id"],
        "status": case["status"],
        "tracking_id": case["tracking_id"],
        "portal": _portal_view(case),
        "primary_road": roads[0],
        "roads": roads,
        "address": (primary or {}).get("address"),
        "ward": (primary or {}).get("ward"),
        "lat": (primary or {}).get("lat"),
        "lon": (primary or {}).get("lon"),
        "road_class": road_class,
        "summary": civic.work_summary(
            roads,
            road_class,
            case["total_potholes"],
            case["patch_area_m2"] or 0.0,
            contractor_name,
            crew_count,
            actual_days,
            promised_days,
            awarded_inr,
            float(verification["effectiveness_pct"]),
        ),
        # Evidence pair: the frame that raised the grievance, and the
        # re-inspection frame that closed it.
        "before_image": (primary or {}).get("annotated_image", ""),
        "after_image": verification.get("annotated_image", ""),
        "before_filename": (primary or {}).get("filename", ""),
        "after_filename": verification.get("filename", ""),
        "potholes_before": int(verification["defects_before"]),
        "potholes_after": int(verification["defects_after"]),
        "effectiveness_pct": float(verification["effectiveness_pct"]),
        "severity_before": (primary or {}).get("severity_score", 0.0),
        "damage_score_before": (primary or {}).get("composite_damage_score", 0.0),
        "damage_score_after": float(verification["damage_score_after"]),
        "reinspection_attempts": int(verification.get("attempts", 1)),
        "patch_area_m2": case["patch_area_m2"] or 0.0,
        "priority": case["priority"],
        "priority_label": case["priority_label"],
        "contractor_name": contractor_name,
        "contractor_specialty": specialty,
        "contractor_rating": float(contractor.get("rating", 0.0)),
        "crew_count": crew_count,
        "promised_days": promised_days,
        "actual_days": actual_days,
        "lifecycle_days": lifecycle_days,
        "estimate_inr": case["estimate_inr"] or 0.0,
        "awarded_inr": awarded_inr,
        "savings_inr": round((case["estimate_inr"] or 0.0) - awarded_inr, 2),
        "charges": civic.charge_summary(boq, awarded_inr or None),
        "boq": boq,
        "sla_state": civic.sla_status(
            case["sla_due_at"], case["awarded_at"], time.time(), spd
        )["sla_state"],
        "sla_hours": case["sla_hours"],
        "officer": case["officer"],
        "submitted_at": case["submitted_at"],
        "acknowledged_at": case["acknowledged_at"],
        "awarded_at": case["awarded_at"],
        "repaired_at": case["repaired_at"],
        "verified_at": case["verified_at"],
        "closed_at": case["closed_at"],
        "seconds_per_sim_day": spd,
        "note": civic.handover_note(
            case["id"],
            case["tracking_id"],
            contractor_name,
            specialty,
            crew_count,
            case["patch_area_m2"] or 0.0,
            case["total_potholes"],
            roads,
            datetime.fromtimestamp(case["repaired_at"] or case["created_at"]).year,
        ),
        "note_issued_at": case["repaired_at"],
    }


def _portal_view(case: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not case["portal_code"]:
        return None
    portal = civic.get_portal(case["portal_code"])
    return {
        "code": portal["code"],
        "name": portal["name"],
        "authority": portal["authority"],
        "department": portal["department"],
        "portal_url": portal["portal_url"],
        "simulated": True,
    }
