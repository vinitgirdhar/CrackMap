"""Printable deliverables for a civic case.

Two documents, both drawn with the app's own palette so a filed grievance looks
like it came from the same system the citizen used:

  * the **dossier** — cover, portal filing record, per-finding evidence, priced
    bill of quantities, re-inspection result and the full audit trail. This is
    the artefact a municipal engineer attaches to the grievance.
  * the **completion certificate** — issued only once an AI re-inspection has
    passed, certifying the repair against the original finding.

Pages are built as a list of draw callables first, so every footer can print a
truthful "Page N of M".
"""

import base64
import io
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg

PAGE_W, PAGE_H = A4
MARGIN = 36
CONTENT_W = PAGE_W - 2 * MARGIN

# CrackMap brand palette — matches front-end/app/globals.css :root tokens.
DARK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#e2e8f0")
BLUE = colors.HexColor("#3b82f6")
GREEN = colors.HexColor("#16a34a")
AMBER = colors.HexColor("#f59e0b")
RED = colors.HexColor("#ef4444")
CHIP_BG = colors.HexColor("#f1f5f9")
WHITE = colors.white

STATUS_COLORS = {
    "DRAFT": MUTED,
    "SUBMITTED": BLUE,
    "ACKNOWLEDGED": BLUE,
    "TENDERED": AMBER,
    "WORK_ORDERED": AMBER,
    "IN_REPAIR": AMBER,
    "REPAIRED": BLUE,
    "VERIFIED": GREEN,
    "CLOSED": GREEN,
}
PRIORITY_COLORS = {"P1": RED, "P2": AMBER, "P3": BLUE, "P4": MUTED}

# Lucide "route" icon — the same glyph rendered next to the wordmark in TopNavBar.tsx.
_ROUTE_ICON_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
     fill="none" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="6" cy="19" r="3"/>
  <path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/>
  <circle cx="18" cy="5" r="3"/>
</svg>
"""

DISCLAIMER = (
    "Filing is SIMULATED: CrackMap models municipal intake behaviour (grievance number format, "
    "owning department, acknowledgement lag, statutory response window) and transmits nothing to "
    "any external authority. Severity and damage scores derive from photographic YOLOv8 detection; "
    "patch areas and rates are indicative estimates, not a certified engineering survey."
)


# ── Primitives ──────────────────────────────────────────────────────────────

def _ts(value: Optional[float], fallback: str = "—") -> str:
    if not value:
        return fallback
    return datetime.fromtimestamp(value).strftime("%d %b %Y, %H:%M")


def _inr(value: Optional[float]) -> str:
    return f"Rs {value:,.0f}" if value else "Rs 0"


def _wrap_text(c: canvas.Canvas, text: str, font: str, size: float, max_width: float) -> List[str]:
    lines: List[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if c.stringWidth(candidate, font, size) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _decode_image(data_uri: str) -> ImageReader:
    _, _, b64 = data_uri.partition(",")
    return ImageReader(io.BytesIO(base64.b64decode(b64)))


def _draw_logo(c: canvas.Canvas, x: float, y: float, icon_size: float = 20) -> None:
    """CrackMap wordmark: Route icon + 'Crack' (dark) + 'Map' (blue)."""
    icon = svg2rlg(io.StringIO(_ROUTE_ICON_SVG))
    scale = icon_size / max(icon.width, icon.height)
    c.saveState()
    c.translate(x, y - icon_size * 0.28)
    c.scale(scale, scale)
    renderPDF.draw(icon, c, 0, 0)
    c.restoreState()

    tx = x + icon_size + 8
    c.setFont("Helvetica-Bold", 17)
    c.setFillColor(DARK)
    c.drawString(tx, y - 6, "Crack")
    c.setFillColor(BLUE)
    c.drawString(tx + c.stringWidth("Crack", "Helvetica-Bold", 17), y - 6, "Map")


def _chip(c: canvas.Canvas, x: float, y: float, text: str, color: colors.Color, filled: bool = False) -> float:
    c.saveState()
    font, size = "Helvetica-Bold", 8.5
    label = text.upper()
    w = c.stringWidth(label, font, size) + 24
    h = 17
    if filled:
        c.setFillColor(color)
        c.setStrokeColor(color)
        text_color = WHITE
    else:
        c.setFillColor(color, alpha=0.12)
        c.setStrokeColor(color)
        text_color = color
    c.roundRect(x, y, w, h, h / 2, fill=1, stroke=1)
    c.setFillColor(text_color)
    c.setFont(font, size)
    c.drawCentredString(x + w / 2, y + 5.5, label)
    c.restoreState()
    return w


def _stat_box(c: canvas.Canvas, x: float, y: float, w: float, label: str, value: str, accent: colors.Color = DARK) -> None:
    h = 46
    c.setFillColor(WHITE)
    c.setStrokeColor(BORDER)
    c.roundRect(x, y, w, h, 8, fill=1, stroke=1)
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x + 9, y + h - 15, label.upper()[:26])
    c.setFillColor(accent)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x + 9, y + 11, value)


def _section(c: canvas.Canvas, y: float, title: str) -> float:
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN, y, title)
    c.setStrokeColor(BORDER)
    c.line(MARGIN, y - 8, PAGE_W - MARGIN, y - 8)
    return y - 26


def _kv_block(c: canvas.Canvas, y: float, rows: List[Tuple[str, str]], label_w: float = 130) -> float:
    for label, value in rows:
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(MARGIN, y, label.upper())
        c.setFillColor(DARK)
        c.setFont("Helvetica", 9)
        for i, line in enumerate(_wrap_text(c, value, "Helvetica", 9, CONTENT_W - label_w)):
            c.drawString(MARGIN + label_w, y - i * 11, line)
            if i:
                y -= 11
        y -= 16
    return y


def _header(c: canvas.Canvas, case: Dict[str, Any], kicker: str) -> float:
    y = PAGE_H - MARGIN
    _draw_logo(c, MARGIN, y)
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawRightString(PAGE_W - MARGIN, y - 3, kicker.upper())
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(PAGE_W - MARGIN, y - 17, f"Case #{case['id']}")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawRightString(PAGE_W - MARGIN, y - 29, case.get("tracking_id") or "Not yet filed")
    y -= 34
    c.setStrokeColor(BORDER)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    return y - 24


def _footer(c: canvas.Canvas, page_no: int, total: int) -> None:
    lines = _wrap_text(c, DISCLAIMER, "Helvetica", 6.5, CONTENT_W - 70)
    top = 26 + 9.5 * len(lines)
    c.setStrokeColor(BORDER)
    c.line(MARGIN, top + 8, PAGE_W - MARGIN, top + 8)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 6.5)
    y = top - 4
    for line in lines:
        c.drawString(MARGIN, y, line)
        y -= 9.5
    c.setFont("Helvetica-Bold", 7)
    c.drawRightString(PAGE_W - MARGIN, top - 4, f"Page {page_no} of {total}")


# ── Dossier pages ───────────────────────────────────────────────────────────

def _page_cover(c: canvas.Canvas, case: Dict[str, Any]) -> None:
    y = _header(c, case, "Road damage grievance dossier")

    status = case["status"]
    w = _chip(c, MARGIN, y - 4, status.replace("_", " "), STATUS_COLORS.get(status, MUTED), filled=True)
    if case.get("priority"):
        w += 8 + _chip(c, MARGIN + w + 8, y - 4, case["priority"], PRIORITY_COLORS.get(case["priority"], MUTED))
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN + w + 12, y, case.get("priority_label") or "Awaiting triage")
    y -= 36

    box_w = (CONTENT_W - 3 * 10) / 4
    awarded = case.get("awarded") or {}
    stats = [
        ("Potholes reported", str(case["total_potholes"]), DARK),
        ("Patch area", f"{case.get('patch_area_m2') or 0} m2", DARK),
        ("Engineer's estimate", _inr(case.get("estimate_inr")), BLUE),
        ("Contract value", _inr(awarded.get("awarded_inr")) if awarded else "Not awarded", GREEN if awarded else MUTED),
    ]
    for i, (label, value, accent) in enumerate(stats):
        _stat_box(c, MARGIN + i * (box_w + 10), y - 46, box_w, label, value, accent)
    y -= 46 + 28

    y = _section(c, y, "Municipal Filing Record")
    portal = case.get("portal")
    if portal:
        sla_text = (
            f"{case.get('sla_hours', 0):.0f}h window, {case.get('sla_state', 'NOT_STARTED').replace('_', ' ').lower()}"
        )
        if case.get("hours_remaining") is not None:
            sla_text += f" ({case['hours_remaining']:+.1f}h)"
        y = _kv_block(
            c,
            y,
            [
                ("Authority", portal["authority"]),
                ("Portal", f"{portal['name']} — {portal['portal_url']}"),
                ("Department", portal["department"]),
                ("Grievance no.", case.get("tracking_id") or "—"),
                ("Assigned officer", case.get("officer") or "Pending acknowledgement"),
                ("Routing basis", case.get("routing_note") or "—"),
                ("Filed / acknowledged", f"{_ts(case.get('submitted_at'))}  /  {_ts(case.get('acknowledged_at'), 'pending')}"),
                ("Response window", sla_text),
            ],
        )
    else:
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(MARGIN, y, "This case is still a draft and has not been filed with any authority.")
        y -= 20

    y -= 10
    y = _section(c, y, "Repair Contract")
    if awarded:
        y = _kv_block(
            c,
            y,
            [
                ("Contractor", f"{awarded['contractor_name']} ({awarded.get('specialty', '')})"),
                ("Rating / crew", f"{awarded.get('rating', 0)} / 5 · {awarded.get('crew_count', 0)} person crew"),
                ("Awarded value", f"{_inr(awarded.get('awarded_inr'))} ({awarded.get('variance_pct', 0):+.1f}% vs estimate)"),
                ("Promised duration", f"{awarded.get('promised_days') or 0:.0f} working day(s)"),
                ("Work order issued", _ts(awarded.get("awarded_at"))),
                ("Repair completed", _ts(case.get("repaired_at"), "in progress")),
            ],
        )
    else:
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 9)
        bids = case.get("bids") or []
        c.drawString(
            MARGIN,
            y,
            f"No contract awarded yet. {len(bids)} bid(s) received." if bids else "No tender floated yet.",
        )


def _finding_card(c: canvas.Canvas, finding: Dict[str, Any], y: float, height: float) -> None:
    c.setFillColor(WHITE)
    c.setStrokeColor(BORDER)
    c.roundRect(MARGIN, y - height, CONTENT_W, height, 8, fill=1, stroke=1)

    img_w = 190.0
    img_h = height - 16
    if finding.get("annotated_image"):
        try:
            c.saveState()
            path = c.beginPath()
            path.roundRect(MARGIN + 8, y - height + 8, img_w, img_h, 5)
            c.clipPath(path, stroke=0)
            c.drawImage(
                _decode_image(finding["annotated_image"]),
                MARGIN + 8, y - height + 8, width=img_w, height=img_h,
                preserveAspectRatio=True, anchor="c", mask="auto",
            )
            c.restoreState()
        except Exception:
            c.restoreState()
            c.setFillColor(CHIP_BG)
            c.roundRect(MARGIN + 8, y - height + 8, img_w, img_h, 5, fill=1, stroke=0)
    else:
        c.setFillColor(CHIP_BG)
        c.roundRect(MARGIN + 8, y - height + 8, img_w, img_h, 5, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(MARGIN + 8 + img_w / 2, y - height + 8 + img_h / 2, "Evidence image unavailable")

    tx = MARGIN + 16 + img_w
    ty = y - 22
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(tx, ty, finding["road_name"][:46])
    ty -= 16

    if finding.get("priority"):
        _chip(c, tx, ty - 5, finding["priority"], PRIORITY_COLORS.get(finding["priority"], MUTED))
        ty -= 24
    else:
        ty -= 4

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8.5)
    coords = (
        f"{finding['lat']:.5f}, {finding['lon']:.5f}"
        if finding.get("lat") is not None
        else "coordinates not captured"
    )
    rows = [
        f"Location: {(finding.get('address') or finding['road_name'])[:58]}",
        f"Coordinates: {coords}   ({finding.get('road_class') or 'Local'} road)",
        f"Potholes detected: {finding['total_defects']}   ·   Severity: {finding['severity_score']}/5",
        f"Damage score: {finding['composite_damage_score']}/100   ·   Patch area: {finding.get('patch_area_m2') or 0} m2",
        f"Source frame: {finding['filename']}",
        f"Logged: {_ts(finding['created_at'])}",
    ]
    for row in rows:
        c.drawString(tx, ty, row)
        ty -= 12


def _page_findings(c: canvas.Canvas, case: Dict[str, Any], findings: List[Dict[str, Any]], part: str) -> None:
    y = _header(c, case, f"Inspected findings {part}")
    y = _section(c, y, "Photographic Evidence")
    card_h = 150.0
    for finding in findings:
        _finding_card(c, finding, y, card_h)
        y -= card_h + 12


def _page_boq(c: canvas.Canvas, case: Dict[str, Any]) -> None:
    y = _header(c, case, "Priced bill of quantities")
    y = _section(c, y, "Bill of Quantities — Bituminous Pothole Repair")
    boq = case.get("boq") or {"lines": [], "subtotal_inr": 0, "net_inr": 0, "gst_inr": 0, "total_inr": 0}

    col_qty, col_rate, col_amt = PAGE_W - MARGIN - 250, PAGE_W - MARGIN - 150, PAGE_W - MARGIN
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(MARGIN, y, "DESCRIPTION")
    c.drawRightString(col_qty, y, "QTY")
    c.drawRightString(col_rate, y, "RATE (RS)")
    c.drawRightString(col_amt, y, "AMOUNT (RS)")
    y -= 6
    c.setStrokeColor(BORDER)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    y -= 16

    for line in boq["lines"]:
        c.setFillColor(DARK)
        c.setFont("Helvetica", 8.5)
        wrapped = _wrap_text(c, line["description"], "Helvetica", 8.5, col_qty - MARGIN - 20)
        c.drawString(MARGIN, y, wrapped[0])
        c.setFillColor(MUTED)
        c.drawRightString(col_qty, y, f"{line['quantity']:g} {line['unit']}")
        c.drawRightString(col_rate, y, f"{line['rate_inr']:,.2f}")
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawRightString(col_amt, y, f"{line['amount_inr']:,.2f}")
        y -= 12
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8.5)
        for extra in wrapped[1:]:
            c.drawString(MARGIN, y, extra)
            y -= 11
        y -= 5

    y -= 4
    c.setStrokeColor(BORDER)
    c.line(col_qty - 40, y, PAGE_W - MARGIN, y)
    y -= 16
    for label, value, bold in [
        ("Subtotal", boq["subtotal_inr"], False),
        ("Net payable before tax", boq["net_inr"], False),
        ("GST @ 18%", boq["gst_inr"], False),
        ("Total engineer's estimate", boq["total_inr"], True),
    ]:
        c.setFillColor(DARK if bold else MUTED)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 9.5 if bold else 8.5)
        c.drawRightString(col_rate, y, label)
        c.drawRightString(col_amt, y, f"{value:,.2f}")
        y -= 15

    awarded = case.get("awarded")
    if awarded and awarded.get("awarded_inr"):
        y -= 12
        y = _section(c, y, "Awarded Against This Estimate")
        y = _kv_block(
            c,
            y,
            [
                ("Contractor", awarded["contractor_name"]),
                ("Quoted value", f"{_inr(awarded['awarded_inr'])} ({awarded.get('variance_pct', 0):+.1f}%)"),
                ("Saving / overrun", _inr((case.get("estimate_inr") or 0) - awarded["awarded_inr"])),
            ],
        )

    c.setFillColor(MUTED)
    c.setFont("Helvetica-Oblique", 7.5)
    for i, line in enumerate(
        _wrap_text(
            c,
            "Patch footprints are inferred from each defect's severity band (Low 0.18 m2, Moderate 0.55 m2, "
            "Severe 1.20 m2) because frame coverage is a 2D photographic proxy. Unit rates sit in the band "
            "published in state Schedule-of-Rates books for bituminous pothole repair.",
            "Helvetica-Oblique", 7.5, CONTENT_W,
        )
    ):
        c.drawString(MARGIN, y - 4 - i * 10, line)


def _page_verification(c: canvas.Canvas, case: Dict[str, Any]) -> None:
    y = _header(c, case, "AI re-inspection result")
    verification = case["verification"]
    passed = verification["passed"]

    y = _section(c, y, "Post-Repair Re-Inspection")
    w = _chip(c, MARGIN, y - 4, "PASSED" if passed else "FAILED — REWORK", GREEN if passed else RED, filled=True)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN + w + 12, y, f"Checked {_ts(verification['checked_at'])} · attempt {verification.get('attempts', 1)}")
    y -= 34

    box_w = (CONTENT_W - 3 * 10) / 4
    for i, (label, value, accent) in enumerate(
        [
            ("Defects before", str(verification["defects_before"]), DARK),
            ("Defects after", str(verification["defects_after"]), GREEN if passed else RED),
            ("Defects cleared", f"{verification['effectiveness_pct']:.0f}%", GREEN if passed else AMBER),
            ("Damage score after", f"{verification['damage_score_after']}/100", DARK),
        ]
    ):
        _stat_box(c, MARGIN + i * (box_w + 10), y - 46, box_w, label, value, accent)
    y -= 46 + 28

    y = _kv_block(
        c,
        y,
        [
            ("After-photo", verification["filename"]),
            ("Severity after", f"{verification['severity_after']}/5"),
            (
                "Pass rule",
                "A repair passes when at most 34% of the originally detected defects remain in the "
                "after-photo, scored by the same YOLOv8 detector that found them.",
            ),
        ],
    )

    if verification.get("annotated_image"):
        y = _section(c, y - 6, "Re-Inspection Frame")
        img_h = min(240.0, y - 110)
        try:
            c.saveState()
            path = c.beginPath()
            path.roundRect(MARGIN, y - img_h, CONTENT_W, img_h, 8)
            c.clipPath(path, stroke=0)
            c.drawImage(
                _decode_image(verification["annotated_image"]),
                MARGIN, y - img_h, width=CONTENT_W, height=img_h,
                preserveAspectRatio=True, anchor="c", mask="auto",
            )
            c.restoreState()
        except Exception:
            c.restoreState()


def _page_audit(c: canvas.Canvas, case: Dict[str, Any], events: List[Dict[str, Any]], part: str) -> None:
    y = _header(c, case, f"Audit trail {part}")
    y = _section(c, y, "Pipeline Event Log")

    for event in events:
        color = STATUS_COLORS.get(event["stage"], MUTED)
        c.setFillColor(color)
        c.circle(MARGIN + 4, y + 3, 3.5, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN + 16, y, event["title"][:92])
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7.5)
        c.drawRightString(PAGE_W - MARGIN, y, _ts(event["created_at"]))
        y -= 11
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(MARGIN + 16, y, event["actor"][:60])
        y -= 11
        if event["detail"]:
            c.setFont("Helvetica", 8)
            for line in _wrap_text(c, event["detail"], "Helvetica", 8, CONTENT_W - 100):
                c.drawString(MARGIN + 16, y, line)
                y -= 10
        y -= 8


def _chunk(items: List[Any], size: int) -> List[List[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)] or [[]]


def generate_dossier_pdf(case: Dict[str, Any]) -> bytes:
    """Full case dossier. `case` is a cases.assemble() view with images included."""
    findings = case.get("findings") or []
    events = case.get("events") or []

    pages: List[Callable[[canvas.Canvas], None]] = [lambda c: _page_cover(c, case)]

    finding_groups = _chunk(findings, 3)
    for i, group in enumerate(finding_groups):
        if not group:
            continue
        part = f"{i + 1} of {len(finding_groups)}" if len(finding_groups) > 1 else ""
        pages.append(lambda c, g=group, p=part: _page_findings(c, case, g, p))

    pages.append(lambda c: _page_boq(c, case))

    if case.get("verification"):
        pages.append(lambda c: _page_verification(c, case))

    event_groups = _chunk(events, 9)
    for i, group in enumerate(event_groups):
        if not group:
            continue
        part = f"{i + 1} of {len(event_groups)}" if len(event_groups) > 1 else ""
        pages.append(lambda c, g=group, p=part: _page_audit(c, case, g, p))

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"CrackMap Case #{case['id']} Dossier")
    total = len(pages)
    for index, draw in enumerate(pages, start=1):
        draw(c)
        _footer(c, index, total)
        c.showPage()
    c.save()
    return buf.getvalue()


def generate_certificate_pdf(case: Dict[str, Any]) -> bytes:
    """Repair completion certificate — only meaningful once verified."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"CrackMap Case #{case['id']} Completion Certificate")

    verification = case.get("verification") or {}
    awarded = case.get("awarded") or {}
    portal = case.get("portal") or {}

    c.setStrokeColor(BORDER)
    c.setLineWidth(2)
    c.roundRect(MARGIN - 8, MARGIN - 8, CONTENT_W + 16, PAGE_H - 2 * MARGIN + 16, 12, fill=0, stroke=1)
    c.setLineWidth(1)

    y = PAGE_H - MARGIN - 26
    _draw_logo(c, MARGIN + 6, y)
    y -= 56

    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(PAGE_W / 2, y, "CERTIFICATE OF REPAIR COMPLETION")
    y -= 30
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(PAGE_W / 2, y, f"Case #{case['id']} — Resolved")
    y -= 22
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 10)
    c.drawCentredString(PAGE_W / 2, y, case.get("tracking_id") or "Unfiled grievance")
    y -= 34

    _chip(
        c,
        PAGE_W / 2 - 60,
        y,
        "AI re-inspection passed" if verification.get("passed") else "Pending verification",
        GREEN if verification.get("passed") else AMBER,
        filled=True,
    )
    y -= 42

    c.setFillColor(DARK)
    c.setFont("Helvetica", 9.5)
    roads = ", ".join(sorted({f["road_name"] for f in (case.get("findings") or [])})) or "—"
    body = (
        f"This certifies that {case['total_potholes']} pothole(s) reported on {roads}, covering an "
        f"estimated {case.get('patch_area_m2') or 0} m2 of carriageway, were repaired under a work order "
        f"issued by the {portal.get('department', 'municipal road cell')} of "
        f"{portal.get('authority', 'the local authority')} and executed by "
        f"{awarded.get('contractor_name', 'the awarded contractor')}. A post-repair re-inspection by the "
        f"same YOLOv8 detector that raised the original finding recorded "
        f"{verification.get('defects_after', 0)} remaining defect(s) against "
        f"{verification.get('defects_before', case['total_potholes'])} before the repair — "
        f"{verification.get('effectiveness_pct', 0):.0f}% of detected defects cleared."
    )
    for line in _wrap_text(c, body, "Helvetica", 9.5, CONTENT_W - 40):
        c.drawString(MARGIN + 20, y, line)
        y -= 14
    y -= 20

    box_w = (CONTENT_W - 3 * 10) / 4
    for i, (label, value, accent) in enumerate(
        [
            ("Potholes repaired", str(case["total_potholes"]), GREEN),
            ("Defects cleared", f"{verification.get('effectiveness_pct', 0):.0f}%", GREEN),
            ("Contract value", _inr(awarded.get("awarded_inr")), DARK),
            ("Response window", case.get("sla_state", "—").replace("_", " ").title(), GREEN if not case.get("breached") else RED),
        ]
    ):
        _stat_box(c, MARGIN + i * (box_w + 10), y - 46, box_w, label, value, accent)
    y -= 46 + 30

    y = _kv_block(
        c,
        y,
        [
            ("Filed", _ts(case.get("submitted_at"))),
            ("Acknowledged", _ts(case.get("acknowledged_at"))),
            ("Work order issued", _ts(awarded.get("awarded_at"))),
            ("Repair completed", _ts(case.get("repaired_at"))),
            ("Re-inspection passed", _ts(case.get("verified_at"))),
            ("Case closed", _ts(case.get("closed_at"), "open")),
            ("Assigned officer", case.get("officer") or "—"),
        ],
    )

    y -= 24
    c.setStrokeColor(BORDER)
    c.line(MARGIN + 20, y, MARGIN + 190, y)
    c.line(PAGE_W - MARGIN - 190, y, PAGE_W - MARGIN - 20, y)
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(MARGIN + 20, y - 12, (awarded.get("contractor_name") or "CONTRACTOR").upper()[:34])
    c.drawRightString(PAGE_W - MARGIN - 20, y - 12, (case.get("officer") or "MUNICIPAL ENGINEER").upper()[:34])

    _footer(c, 1, 1)
    c.showPage()
    c.save()
    return buf.getvalue()


def demo_self_check() -> None:
    """Renders both documents from a synthetic case and asserts real PDF bytes."""
    import time

    now = time.time()
    case = {
        "id": 7,
        "status": "CLOSED",
        "total_potholes": 5,
        "avg_severity": 3.8,
        "priority": "P2",
        "priority_label": "High",
        "patch_area_m2": 2.2,
        "estimate_inr": 12500.0,
        "tracking_id": "MCGM/RTD/2026/00007",
        "routing_note": "Coordinate falls inside the Brihanmumbai Municipal Corporation municipal limit.",
        "officer": "Ward Engineer — R. Shaikh",
        "submitted_at": now - 500,
        "acknowledged_at": now - 480,
        "sla_hours": 72.0,
        "sla_state": "MET",
        "hours_remaining": 14.2,
        "breached": False,
        "repaired_at": now - 60,
        "verified_at": now - 30,
        "closed_at": now,
        "portal": {
            "code": "MCGM",
            "name": "MCGM Pothole Fixit — Voice of Citizen",
            "authority": "Brihanmumbai Municipal Corporation",
            "department": "Roads & Traffic Department",
            "portal_url": "https://portal.mcgm.gov.in",
            "simulated": True,
        },
        "boq": {
            "area_m2": 2.2,
            "lines": [
                {"description": "Bituminous concrete hot-mix patch, 50 mm compacted", "unit": "m2", "quantity": 2.2, "rate_inr": 1450.0, "amount_inr": 3190.0},
                {"description": "Traffic management, barricading & safety signage", "unit": "lump sum", "quantity": 1.0, "rate_inr": 255.2, "amount_inr": 255.2},
            ],
            "subtotal_inr": 3190.0,
            "net_inr": 3445.2,
            "gst_inr": 620.14,
            "total_inr": 4065.34,
        },
        "bids": [],
        "awarded": {
            "contractor_id": 3,
            "contractor_name": "SafeStreet Civil Works",
            "specialty": "Emergency 24h repair",
            "rating": 4.7,
            "crew_count": 4,
            "awarded_inr": 11800.0,
            "promised_days": 3.0,
            "variance_pct": -5.6,
            "awarded_at": now - 400,
        },
        "verification": {
            "filename": "after.jpg",
            "defects_before": 5,
            "defects_after": 1,
            "remaining_ratio": 0.2,
            "effectiveness_pct": 80.0,
            "severity_after": 1.5,
            "damage_score_after": 88.0,
            "annotated_image": "",
            "passed": True,
            "checked_at": now - 30,
            "attempts": 1,
        },
        "findings": [
            {
                "id": 1,
                "filename": "frame_001.jpg",
                "road_name": "Hill Road, Bandra West",
                "address": "Hill Road, Bandra West, Mumbai, Maharashtra",
                "road_class": "Collector",
                "lat": 19.0596,
                "lon": 72.8295,
                "total_defects": 5,
                "severity_score": 3.8,
                "composite_damage_score": 42.0,
                "patch_area_m2": 2.2,
                "priority": "P2",
                "created_at": now - 900,
                "annotated_image": "",
            }
        ],
        "events": [
            {"stage": "DRAFT", "actor": "CrackMap Triage Engine", "title": "Case #7 opened", "detail": "5 potholes across 2.2 m2.", "created_at": now - 900},
            {"stage": "CLOSED", "actor": "Roads & Traffic Department", "title": "Case closed", "detail": "Certificate issued.", "created_at": now},
        ],
    }

    dossier = generate_dossier_pdf(case)
    assert dossier.startswith(b"%PDF"), "dossier is not a PDF"
    assert len(dossier) > 4000, len(dossier)
    # cover + findings + boq + verification + audit
    assert dossier.count(b"/Type /Page\n") >= 4 or b"/Count 5" in dossier, "unexpected dossier page count"

    certificate = generate_certificate_pdf(case)
    assert certificate.startswith(b"%PDF")
    assert len(certificate) > 2000

    # A bare draft must still render without a portal, award or verification.
    draft = {
        **case,
        "status": "DRAFT",
        "portal": None,
        "tracking_id": None,
        "awarded": None,
        "verification": None,
        "bids": [],
        "events": [],
        "findings": [],
    }
    assert generate_dossier_pdf(draft).startswith(b"%PDF")
    print("report_pdf.py self-check OK")


if __name__ == "__main__":
    demo_self_check()
