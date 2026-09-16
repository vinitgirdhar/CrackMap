"""Civic pipeline domain logic.

Pure functions only — no database access. Everything here answers one of:
  * which municipal body owns this coordinate,
  * how urgent is this defect and what response time does that imply,
  * what would the repair cost (bill of quantities),
  * given the timestamps on a case, what stage is it actually in right now.

The last point is the important one: stages that a real municipality reaches by
the passage of time (portal acknowledgement, crew mobilisation, repair
progress) are *derived from timestamps*, never from a button press. A simulated
clock compresses days into seconds so a demo can watch it happen.
"""

import hashlib
import math
from typing import Any, Dict, List, Optional, Tuple

# ── Simulated clock ──────────────────────────────────────────────────────────
# One municipal working day is compressed into this many wall-clock seconds so
# the whole intake -> repair -> verification cycle is watchable in a demo.
# Override with SIM_SECONDS_PER_DAY to slow it down toward real time.
SECONDS_PER_SIM_DAY_DEFAULT = 12.0


def sim_days_elapsed(since: float, now: float, seconds_per_day: float) -> float:
    """Simulated municipal days between two real unix timestamps."""
    return max(0.0, (now - since) / max(0.001, seconds_per_day))


def sim_day_to_real_seconds(days: float, seconds_per_day: float) -> float:
    return days * seconds_per_day


# ── Municipal portal registry ───────────────────────────────────────────────
# Real, publicly documented civic grievance channels. Filing is SIMULATED:
# nothing is transmitted, we only model the intake behaviour (grievance number
# format, owning department, acknowledgement lag, statutory response window).

PORTALS: List[Dict[str, Any]] = [
    {
        "code": "MCGM",
        "name": "MCGM Pothole Fixit — Voice of Citizen",
        "authority": "Brihanmumbai Municipal Corporation",
        "department": "Roads & Traffic Department",
        "portal_url": "https://portal.mcgm.gov.in",
        "tracking_format": "MCGM/RTD/{year}/{seq:05d}",
        "bbox": (18.86, 72.76, 19.28, 72.99),
        "officers": [
            "Exec. Engineer (Roads) — A. Kulkarni",
            "Dy. Engineer (Roads) — S. Pawar",
            "Ward Engineer — R. Shaikh",
        ],
    },
    {
        "code": "PMC",
        "name": "PMC CARE Citizen Grievance",
        "authority": "Pune Municipal Corporation",
        "department": "Road Department",
        "portal_url": "https://pmc.gov.in",
        "tracking_format": "PMC-CARE-{year}-{seq:05d}",
        "bbox": (18.39, 73.70, 18.66, 73.99),
        "officers": ["Exec. Engineer (Roads) — M. Deshpande", "Junior Engineer — P. Jadhav"],
    },
    {
        "code": "NMMC",
        "name": "NMMC Citizen Services Grievance Cell",
        "authority": "Navi Mumbai Municipal Corporation",
        "department": "City Engineering Department",
        "portal_url": "https://www.nmmc.gov.in",
        "tracking_format": "NMMC/CE/{year}/{seq:05d}",
        "bbox": (18.94, 72.96, 19.16, 73.12),
        "officers": ["City Engineer's Office — V. Naik", "Ward Engineer — D. Patil"],
    },
    {
        "code": "TMC",
        "name": "Thane Municipal Corporation Grievance Portal",
        "authority": "Thane Municipal Corporation",
        "department": "Public Works Department",
        "portal_url": "https://www.thanecity.gov.in",
        "tracking_format": "TMC/PWD/{year}/{seq:05d}",
        "bbox": (19.16, 72.92, 19.30, 73.10),
        "officers": ["Exec. Engineer (PWD) — K. Bhoir", "Dy. Engineer — A. More"],
    },
    {
        "code": "GMC-DEL",
        "name": "MCD 311 Citizen Grievance",
        "authority": "Municipal Corporation of Delhi",
        "department": "Engineering Department (Roads)",
        "portal_url": "https://mcdonline.nic.in",
        "tracking_format": "MCD/ENG/{year}/{seq:05d}",
        "bbox": (28.40, 76.84, 28.88, 77.35),
        "officers": ["Exec. Engineer (Roads) — N. Yadav", "Junior Engineer — S. Verma"],
    },
    {
        "code": "BBMP",
        "name": "BBMP Sahaaya 2.0",
        "authority": "Bruhat Bengaluru Mahanagara Palike",
        "department": "Road Infrastructure Division",
        "portal_url": "https://sahaaya2.bbmp.gov.in",
        "tracking_format": "BBMP/RI/{year}/{seq:05d}",
        "bbox": (12.80, 77.44, 13.14, 77.78),
        "officers": ["Exec. Engineer (Roads) — H. Gowda", "Asst. Engineer — L. Rao"],
    },
]

# Used when a coordinate falls outside every mapped jurisdiction, or when no
# coordinate was captured at all.
FALLBACK_PORTAL: Dict[str, Any] = {
    "code": "PWD",
    "name": "State Public Works Department — General Intake",
    "authority": "Public Works Department",
    "department": "Roads & Bridges Wing",
    "portal_url": "https://pwd.gov.in",
    "tracking_format": "PWD/GEN/{year}/{seq:05d}",
    "bbox": None,
    "officers": ["Exec. Engineer (Roads)", "Sub-Divisional Engineer"],
}


def route_to_portal(lat: Optional[float], lon: Optional[float]) -> Tuple[Dict[str, Any], str]:
    """Pick the municipal body that owns this coordinate.

    Returns the portal record plus a human-readable routing justification, so
    the UI can always explain *why* a case landed where it did.
    """
    if lat is None or lon is None:
        return FALLBACK_PORTAL, "No coordinate captured — routed to the state PWD general intake."

    for portal in PORTALS:
        lat_min, lon_min, lat_max, lon_max = portal["bbox"]
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return portal, f"Coordinate falls inside the {portal['authority']} municipal limit."

    return (
        FALLBACK_PORTAL,
        "Coordinate is outside every mapped municipal limit — routed to the state PWD general intake.",
    )


def get_portal(code: str) -> Dict[str, Any]:
    for portal in PORTALS:
        if portal["code"] == code:
            return portal
    return FALLBACK_PORTAL


def format_tracking_id(portal: Dict[str, Any], year: int, seq: int) -> str:
    return portal["tracking_format"].format(year=year, seq=seq)


def pick_officer(portal: Dict[str, Any], seed: str) -> str:
    """Deterministic officer assignment — same case always shows the same name."""
    officers = portal["officers"]
    digest = hashlib.sha1(seed.encode()).digest()
    return officers[digest[0] % len(officers)]


# ── Road classification & priority ──────────────────────────────────────────

# OpenStreetMap highway tag -> functional road class, which drives both
# priority weighting and the statutory response window.
_OSM_ROAD_CLASS = {
    "motorway": "Arterial",
    "motorway_link": "Arterial",
    "trunk": "Arterial",
    "trunk_link": "Arterial",
    "primary": "Arterial",
    "primary_link": "Arterial",
    "secondary": "Collector",
    "secondary_link": "Collector",
    "tertiary": "Collector",
    "tertiary_link": "Collector",
    "residential": "Local",
    "unclassified": "Local",
    "service": "Local",
    "living_street": "Local",
}

ROAD_CLASS_WEIGHT = {"Arterial": 1.0, "Collector": 0.7, "Local": 0.45}


def classify_road(osm_type: Optional[str]) -> str:
    if not osm_type:
        return "Local"
    return _OSM_ROAD_CLASS.get(osm_type.lower(), "Local")


# Priority bands. Response hours are modelled on the 24h/72h/7d/30d ladder
# municipal road cells commonly publish for pothole grievances.
PRIORITY_BANDS = [
    {"code": "P1", "label": "Critical — Safety Hazard", "min_score": 72.0, "sla_hours": 24},
    {"code": "P2", "label": "High", "min_score": 52.0, "sla_hours": 72},
    {"code": "P3", "label": "Medium", "min_score": 30.0, "sla_hours": 168},
    {"code": "P4", "label": "Low — Routine Maintenance", "min_score": 0.0, "sla_hours": 720},
]


def assess_priority(
    severity_score: float,
    total_defects: int,
    road_class: str,
) -> Dict[str, Any]:
    """Score a finding 0-100 and map it onto a priority band + response window.

    Weights: severity dominates, defect count next, road function last. A single
    shallow pothole on a residential lane must not outrank a cluster of deep
    ones on an arterial road.
    """
    severity_component = min(1.0, max(0.0, severity_score / 5.0)) * 55.0
    density_component = min(1.0, total_defects / 8.0) * 25.0
    road_component = ROAD_CLASS_WEIGHT.get(road_class, 0.45) * 20.0
    score = round(severity_component + density_component + road_component, 1)

    band = next(b for b in PRIORITY_BANDS if score >= b["min_score"])
    return {
        "priority": band["code"],
        "priority_label": band["label"],
        "priority_score": score,
        "sla_hours": float(band["sla_hours"]),
        "road_class": road_class,
    }


# ── Repair cost: bill of quantities ─────────────────────────────────────────

# Patch footprint implied by each severity band. Frame coverage is a 2D proxy,
# so these are declared estimates, not survey measurements.
PATCH_AREA_M2 = {"Low": 0.18, "Moderate": 0.55, "Severe": 1.20, "Critical": 1.60}
DEFAULT_PATCH_AREA_M2 = 0.55

# Unit rates in INR/m², in the band published in state Schedule-of-Rates books
# for bituminous pothole repair. ponytail: flat rates; swap for the live SoR
# feed if this ever needs to be tender-grade.
BOQ_ITEMS = [
    ("Saw-cutting & removal of distressed bituminous layer", "m²", 320.0),
    ("Tack coat (SS-1 bitumen emulsion) @ 0.30 kg/m²", "m²", 42.0),
    ("Bituminous concrete hot-mix patch, 50 mm compacted", "m²", 1450.0),
    ("Compaction, edge sealing & surface finishing", "m²", 165.0),
]
TRAFFIC_MANAGEMENT_PCT = 0.08
CONTINGENCY_PCT = 0.05
GST_PCT = 0.18


def patch_area_m2(boxes: List[Dict[str, Any]]) -> float:
    """Estimated total patch footprint for one inspection's detected defects."""
    if not boxes:
        return 0.0
    return round(
        sum(PATCH_AREA_M2.get(b.get("severity", ""), DEFAULT_PATCH_AREA_M2) for b in boxes), 2
    )


def build_boq(total_area_m2: float) -> Dict[str, Any]:
    """Priced bill of quantities for a patch area. This is the costed output a
    municipal engineer would attach to a work order."""
    area = max(0.0, round(total_area_m2, 2))
    lines = []
    subtotal = 0.0
    for description, unit, rate in BOQ_ITEMS:
        amount = round(area * rate, 2)
        subtotal += amount
        lines.append(
            {
                "description": description,
                "unit": unit,
                "quantity": area,
                "rate_inr": rate,
                "amount_inr": amount,
            }
        )

    traffic = round(subtotal * TRAFFIC_MANAGEMENT_PCT, 2)
    lines.append(
        {
            "description": "Traffic management, barricading & safety signage",
            "unit": "lump sum",
            "quantity": 1.0,
            "rate_inr": traffic,
            "amount_inr": traffic,
        }
    )
    contingency = round((subtotal + traffic) * CONTINGENCY_PCT, 2)
    lines.append(
        {
            "description": "Contingency provision",
            "unit": "lump sum",
            "quantity": 1.0,
            "rate_inr": contingency,
            "amount_inr": contingency,
        }
    )

    net = round(subtotal + traffic + contingency, 2)
    gst = round(net * GST_PCT, 2)
    return {
        "area_m2": area,
        "lines": lines,
        "subtotal_inr": round(subtotal, 2),
        "net_inr": net,
        "gst_inr": gst,
        "total_inr": round(net + gst, 2),
    }


def repair_duration_days(total_area_m2: float) -> float:
    """Crew-days for the patch work. One crew resurfaces roughly 12 m²/day
    including curing, with a one-day floor for mobilisation-only jobs."""
    return float(min(10, max(1, math.ceil(total_area_m2 / 12.0))))


# ── Contractor bidding ──────────────────────────────────────────────────────

# Each contractor quotes off the BOQ with their own multiplier. Deterministic
# per (case, contractor) so a reload never reshuffles a live tender.
def generate_bids(
    case_id: int,
    contractors: List[Dict[str, Any]],
    boq_total: float,
    duration_days: float,
) -> List[Dict[str, Any]]:
    bids = []
    for contractor in contractors:
        digest = hashlib.sha1(f"{case_id}:{contractor['id']}".encode()).digest()
        # Quote between 0.88x and 1.18x of the engineer's estimate.
        multiplier = 0.88 + (digest[0] / 255.0) * 0.30
        # Faster crews quote higher; slower ones discount.
        day_offset = (digest[1] % 5) - 2
        bids.append(
            {
                "contractor_id": contractor["id"],
                "contractor_name": contractor["name"],
                "specialty": contractor["specialty"],
                "service_area": contractor["service_area"],
                "rating": contractor.get("rating", 4.0),
                "quoted_inr": round(boq_total * multiplier, 2),
                "variance_pct": round((multiplier - 1.0) * 100.0, 1),
                "promised_days": float(max(1, duration_days + day_offset)),
            }
        )
    return sorted(bids, key=lambda b: b["quoted_inr"])


# ── Case stage machine ──────────────────────────────────────────────────────

STAGES = [
    {"key": "DRAFT", "label": "Intake & Triage", "actor": "Field Inspector"},
    {"key": "SUBMITTED", "label": "Filed to Portal", "actor": "CrackMap Filing Agent"},
    {"key": "ACKNOWLEDGED", "label": "Acknowledged by Authority", "actor": "Municipal Portal"},
    {"key": "TENDERED", "label": "Tender & Bidding", "actor": "Municipal Engineer"},
    {"key": "WORK_ORDERED", "label": "Work Order Issued", "actor": "Municipal Engineer"},
    {"key": "IN_REPAIR", "label": "Repair In Progress", "actor": "Contractor Crew"},
    {"key": "REPAIRED", "label": "Awaiting Re-Inspection", "actor": "Contractor Crew"},
    {"key": "VERIFIED", "label": "Re-Inspection Passed", "actor": "CrackMap AI"},
    {"key": "CLOSED", "label": "Case Closed", "actor": "Municipal Engineer"},
]
STAGE_KEYS = [s["key"] for s in STAGES]
STAGE_INDEX = {s["key"]: i for i, s in enumerate(STAGES)}

# Simulated lags for the transitions a municipality reaches without anyone
# clicking anything, in simulated municipal days.
ACK_LAG_DAYS = 0.5
MOBILISATION_LAG_DAYS = 1.0

# A verification passes when the re-inspection finds at most this share of the
# originally detected defects still present.
VERIFICATION_PASS_RATIO = 0.34


def stage_index(status: str) -> int:
    return STAGE_INDEX.get(status, 0)


def repair_progress(
    awarded_at: Optional[float],
    promised_days: float,
    now: float,
    seconds_per_day: float,
) -> Dict[str, Any]:
    """Crew mobilisation + repair completion, derived purely from the clock."""
    if awarded_at is None:
        return {"progress_pct": 0.0, "sim_days_elapsed": 0.0, "mobilised": False, "complete": False}

    elapsed = sim_days_elapsed(awarded_at, now, seconds_per_day)
    work_elapsed = max(0.0, elapsed - MOBILISATION_LAG_DAYS)
    progress = min(1.0, work_elapsed / max(0.25, promised_days))
    return {
        "progress_pct": round(progress * 100.0, 1),
        "sim_days_elapsed": round(elapsed, 2),
        "mobilised": elapsed >= MOBILISATION_LAG_DAYS,
        "complete": progress >= 1.0,
    }


def sla_deadline(acknowledged_at: float, sla_hours: float, seconds_per_day: float) -> float:
    """Real timestamp by which the statutory window expires.

    The window is quoted in municipal hours but elapses on the simulated clock,
    so a 24-hour P1 target is one simulated day of wall-clock time.
    """
    return acknowledged_at + sim_day_to_real_seconds(sla_hours / 24.0, seconds_per_day)


def sla_status(
    sla_due_at: Optional[float],
    responded_at: Optional[float],
    now: float,
    seconds_per_day: float,
) -> Dict[str, Any]:
    """Whether the statutory response window was met.

    The window is a *response* deadline, not a completion deadline: a municipal
    road cell commits to issuing a work order within so many hours of
    acknowledging a grievance, not to finishing the asphalt in that time. So the
    clock stops at `responded_at` (when the work order was issued) and runs
    against `now` until then.

    `hours_remaining` is in simulated municipal hours, matching how the window
    was quoted to the citizen.
    """
    if sla_due_at is None:
        return {"sla_state": "NOT_STARTED", "hours_remaining": None, "breached": False}

    reference = responded_at if responded_at is not None else now
    hours_remaining = round(
        sim_days_elapsed(reference, sla_due_at, seconds_per_day) * 24.0
        if sla_due_at >= reference
        else -sim_days_elapsed(sla_due_at, reference, seconds_per_day) * 24.0,
        1,
    )
    if responded_at is not None:
        return {
            "sla_state": "MET" if hours_remaining >= 0 else "BREACHED",
            "hours_remaining": hours_remaining,
            "breached": hours_remaining < 0,
        }
    if hours_remaining < 0:
        return {"sla_state": "BREACHED", "hours_remaining": hours_remaining, "breached": True}
    if hours_remaining < 24:
        return {"sla_state": "AT_RISK", "hours_remaining": hours_remaining, "breached": False}
    return {"sla_state": "ON_TRACK", "hours_remaining": hours_remaining, "breached": False}


def severity_band(avg_score: float) -> Tuple[str, str, Tuple[int, int, int]]:
    """Severity label + colour for an averaged 0-5 score."""
    if avg_score < 2.0:
        return "Low", "#22c55e", (34, 197, 94)
    if avg_score < 4.0:
        return "Moderate", "#f59e0b", (245, 158, 11)
    return "Severe", "#ef4444", (239, 68, 68)


# ── Completed-work record ───────────────────────────────────────────────────
# What a contractor hands over when the patch is done, and how the money on it
# is summarised for a citizen-facing record.

# Defect liability period by the kind of work the contractor was empanelled
# for, in months. Bituminous reconstruction and resurfacing carry the longest
# guarantee; an emergency overnight patch the shortest.
_LIABILITY_MONTHS = (
    ("reconstruction", 24),
    ("resurfacing", 24),
    ("micro-surfacing", 18),
    ("crack sealing", 12),
    ("patching", 12),
    ("emergency", 6),
)
DEFAULT_LIABILITY_MONTHS = 12


def defect_liability_months(specialty: str) -> int:
    lowered = (specialty or "").lower()
    for keyword, months in _LIABILITY_MONTHS:
        if keyword in lowered:
            return months
    return DEFAULT_LIABILITY_MONTHS


def traffic_reopen_hours(total_area_m2: float) -> int:
    """Hours before the lane goes back to traffic, driven by curing time."""
    return int(min(12, max(4, 4 + math.ceil(max(0.0, total_area_m2) / 2.0))))


def handover_note(
    case_id: int,
    tracking_id: Optional[str],
    contractor_name: str,
    contractor_specialty: str,
    crew_count: int,
    total_area_m2: float,
    total_potholes: int,
    roads: List[str],
    year: int,
) -> Dict[str, Any]:
    """The contractor's work-completion notice.

    Templated from the case's own facts — this is a simulated contractor, so the
    wording is generated rather than written, but every number in it is the real
    number recorded against the work order.
    """
    initials = "".join(word[0] for word in contractor_name.split()[:3] if word[:1].isalpha()).upper()
    digest = hashlib.sha1(f"note-{case_id}".encode()).digest()
    reference = f"{initials or 'CON'}/WC/{year}/{(digest[0] << 8 | digest[1]) % 9000 + 1000}"

    months = defect_liability_months(contractor_specialty)
    hours = traffic_reopen_hours(total_area_m2)
    where = roads[0] if roads else "the reported location"
    extra = f" and {len(roads) - 1} adjoining stretch(es)" if len(roads) > 1 else ""

    statement = (
        f"Work under {tracking_id or f'case #{case_id}'} at {where}{extra} is complete. "
        f"Our {crew_count}-person crew saw-cut and removed the distressed bituminous layer over "
        f"{total_area_m2} m², applied an SS-1 bitumen emulsion tack coat, and laid a 50 mm "
        f"compacted bituminous concrete patch across {total_potholes} pothole"
        f"{'' if total_potholes == 1 else 's'}, finishing with edge sealing and surface regulation. "
        f"The carriageway was reopened to traffic {hours} hours after final compaction. "
        f"The patch carries a {months}-month defect liability period from the date of completion."
    )

    return {
        "reference": reference,
        "statement": statement,
        "materials": (
            "Bituminous concrete (hot-mix) · SS-1 bitumen emulsion tack coat · "
            "50 mm compacted thickness"
        ),
        "defect_liability_months": months,
        "traffic_reopened_after_hours": hours,
        "signed_by": f"{contractor_name} — Site Engineer",
    }


def work_summary(
    roads: List[str],
    road_class: str,
    total_potholes: int,
    total_area_m2: float,
    contractor_name: str,
    crew_count: int,
    actual_days: float,
    promised_days: float,
    awarded_inr: float,
    effectiveness_pct: float,
) -> str:
    """One-paragraph plain-language account of what was done to the road."""
    where = ", ".join(roads[:2]) + (f" +{len(roads) - 2} more" if len(roads) > 2 else "")
    pace = (
        "inside the promised window"
        if actual_days <= promised_days
        else f"{actual_days - promised_days:.1f} day(s) past the promised window"
    )
    return (
        f"Patched {total_potholes} pothole{'' if total_potholes == 1 else 's'} across "
        f"{total_area_m2} m² of {road_class.lower()} carriageway on {where}. "
        f"{contractor_name} completed the work with a {crew_count}-person crew in "
        f"{actual_days:.1f} of {promised_days:.0f} promised day(s) — {pace} — for a contract value "
        f"of Rs {awarded_inr:,.0f}. A post-repair AI re-inspection cleared "
        f"{effectiveness_pct:.0f}% of the originally detected defects."
    )


def charge_summary(boq: Dict[str, Any], awarded_inr: Optional[float]) -> List[Dict[str, Any]]:
    """The bill collapsed into the few lines a citizen-facing record needs.

    Rate-based items are one 'pavement works' figure; the lump sums, tax and the
    awarded value stay visible on their own, because those are the numbers
    people actually query.
    """
    works = sum(line["amount_inr"] for line in boq["lines"] if line["unit"] != "lump sum")
    charges = [
        {
            "label": "Pavement works",
            "note": "Saw-cutting, tack coat, 50 mm hot-mix patch, compaction & edge sealing",
            "amount_inr": round(works, 2),
        }
    ]
    for line in boq["lines"]:
        if line["unit"] == "lump sum":
            charges.append(
                {"label": line["description"], "note": "", "amount_inr": line["amount_inr"]}
            )
    charges.append(
        {"label": "GST @ 18%", "note": "On the net payable", "amount_inr": boq["gst_inr"]}
    )
    charges.append(
        {
            "label": "Engineer's estimate",
            "note": "Priced from the bill of quantities before tender",
            "amount_inr": boq["total_inr"],
        }
    )
    if awarded_inr is not None:
        delta = boq["total_inr"] - awarded_inr
        charges.append(
            {
                "label": "Awarded contract value",
                "note": (
                    f"Rs {abs(delta):,.0f} {'below' if delta >= 0 else 'above'} the estimate"
                ),
                "amount_inr": round(awarded_inr, 2),
            }
        )
    return charges


def demo_self_check() -> None:
    """Smallest runnable check that fails if the domain rules break."""
    portal, why = route_to_portal(19.076, 72.8777)
    assert portal["code"] == "MCGM", portal
    assert "Brihanmumbai" in why
    assert route_to_portal(None, None)[0]["code"] == "PWD"
    assert route_to_portal(-33.86, 151.20)[0]["code"] == "PWD"

    assert classify_road("primary") == "Arterial"
    assert classify_road("residential") == "Local"
    assert classify_road(None) == "Local"

    hazard = assess_priority(5.0, 8, "Arterial")
    routine = assess_priority(1.5, 1, "Local")
    assert hazard["priority"] == "P1", hazard
    assert routine["priority"] == "P4", routine
    assert hazard["priority_score"] > routine["priority_score"]
    assert hazard["sla_hours"] < routine["sla_hours"]

    boq = build_boq(1.1)
    assert boq["total_inr"] > boq["net_inr"] > boq["subtotal_inr"] > 0
    assert abs(boq["gst_inr"] - round(boq["net_inr"] * GST_PCT, 2)) < 0.01
    assert build_boq(0.0)["total_inr"] == 0.0

    assert patch_area_m2([{"severity": "Severe"}, {"severity": "Low"}]) == 1.38
    assert repair_duration_days(0.5) == 1.0
    assert repair_duration_days(200.0) == 10.0

    bids = generate_bids(1, [{"id": i, "name": f"C{i}", "specialty": "s", "service_area": "a"} for i in range(1, 6)], 100000.0, 3.0)
    assert len(bids) == 5
    assert bids == sorted(bids, key=lambda b: b["quoted_inr"])
    assert all(b["promised_days"] >= 1 for b in bids)
    # Deterministic: same inputs, same quotes.
    assert generate_bids(1, [{"id": 2, "name": "C", "specialty": "s", "service_area": "a"}], 100000.0, 3.0)[0]["quoted_inr"] == next(
        b["quoted_inr"] for b in bids if b["contractor_id"] == 2
    )

    fresh = repair_progress(1000.0, 2.0, 1000.0, 10.0)
    assert fresh["progress_pct"] == 0.0 and not fresh["mobilised"]
    mid = repair_progress(1000.0, 2.0, 1000.0 + 20.0, 10.0)
    assert 0.0 < mid["progress_pct"] < 100.0, mid
    done = repair_progress(1000.0, 2.0, 1000.0 + 40.0, 10.0)
    assert done["complete"] and done["progress_pct"] == 100.0
    assert repair_progress(None, 2.0, 5000.0, 10.0)["progress_pct"] == 0.0

    assert sla_status(None, None, 0.0, 12.0)["sla_state"] == "NOT_STARTED"
    # 12s per simulated day, so a 6s gap is 12 simulated hours -> at risk.
    assert sla_status(1006.0, None, 1000.0, 12.0)["sla_state"] == "AT_RISK"
    assert sla_status(1000.0 + 24.0, None, 1000.0, 12.0)["sla_state"] == "ON_TRACK"
    breached = sla_status(1000.0, None, 1030.0, 12.0)
    assert breached["breached"] is True and breached["hours_remaining"] < 0
    # The clock stops when the work order is issued, not when the case closes.
    assert sla_status(1000.0, 500.0, 999999.0, 12.0)["sla_state"] == "MET"
    assert sla_status(1000.0, 1024.0, 999999.0, 12.0)["sla_state"] == "BREACHED"
    assert sla_deadline(1000.0, 24.0, 12.0) == 1012.0
    assert sla_deadline(1000.0, 72.0, 12.0) == 1036.0

    assert severity_band(1.0)[0] == "Low"
    assert severity_band(3.0)[0] == "Moderate"
    assert severity_band(4.5)[0] == "Severe"

    assert defect_liability_months("Full-depth reconstruction") == 24
    assert defect_liability_months("Hot-mix pothole patching") == 12
    assert defect_liability_months("Emergency 24h repair") == 6
    assert defect_liability_months("") == DEFAULT_LIABILITY_MONTHS
    assert traffic_reopen_hours(0.0) == 4
    assert traffic_reopen_hours(2.0) == 5
    assert traffic_reopen_hours(500.0) == 12

    note = handover_note(
        7, "MCGM/RTD/2026/00007", "SafeStreet Civil Works", "Emergency 24h repair",
        4, 2.2, 5, ["Hill Road, Bandra West"], 2026,
    )
    assert note["reference"].startswith("SCW/WC/2026/"), note["reference"]
    assert note["defect_liability_months"] == 6
    assert "2.2 m²" in note["statement"] and "5 potholes" in note["statement"]
    assert "MCGM/RTD/2026/00007" in note["statement"]
    assert note["signed_by"].startswith("SafeStreet Civil Works")
    # Deterministic: the same case always yields the same reference.
    assert handover_note(7, "MCGM/RTD/2026/00007", "SafeStreet Civil Works",
                         "Emergency 24h repair", 4, 2.2, 5,
                         ["Hill Road, Bandra West"], 2026)["reference"] == note["reference"]
    # Singular phrasing and the multi-road suffix both hold.
    one = handover_note(1, None, "Konkan Asphalt & Paving Co.", "Hot-mix pothole patching",
                        6, 0.5, 1, ["A Road", "B Road"], 2026)
    assert "1 pothole." in one["statement"] or "1 pothole," in one["statement"]
    assert "adjoining stretch" in one["statement"]
    assert "case #1" in one["statement"]

    summary = work_summary(["Hill Road"], "Collector", 5, 2.2, "SafeStreet Civil Works",
                           4, 1.5, 2.0, 11800.0, 80.0)
    assert "5 potholes" in summary and "inside the promised window" in summary
    assert "80%" in summary
    late = work_summary(["Hill Road"], "Arterial", 1, 0.5, "X", 3, 4.0, 2.0, 100.0, 50.0)
    assert "past the promised window" in late

    boq = build_boq(2.0)
    charges = charge_summary(boq, 9000.0)
    labels = [c["label"] for c in charges]
    assert labels[0] == "Pavement works"
    assert "GST @ 18%" in labels and "Awarded contract value" in labels
    # The works figure must exclude the lump sums it sits alongside.
    lump = sum(line["amount_inr"] for line in boq["lines"] if line["unit"] == "lump sum")
    assert abs(charges[0]["amount_inr"] + lump - boq["subtotal_inr"] - lump) < 0.01
    assert charge_summary(boq, None)[-1]["label"] == "Engineer's estimate"
    print("civic.py self-check OK")


if __name__ == "__main__":
    demo_self_check()
