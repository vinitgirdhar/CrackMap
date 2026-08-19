"""
CrackMap UI Components — Clean Enterprise Design System.
Inspired by Salesforce executive dashboards: light canvas, pill navigation,
pastel metric cards, dark feature panels, clean typography.
"""

import pandas as pd
import numpy as np
import pydeck as pdk
from src.config import DAMAGE_CLASSES


# ─────────────────────────────────────────────
# CSS: minimal, targeted overrides that work
# WITH Streamlit's light theme, not against it
# ─────────────────────────────────────────────
MODERN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── Base reset ── */
html, body, [class*="css"], .stApp,
.stMarkdown, .stMarkdown p, .stMarkdown h1,
.stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
.stMarkdown span, .stMarkdown li, .stMarkdown td,
.stMarkdown th, .stMarkdown div {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.stApp {
    background: #f8fafc !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown h3,
section[data-testid="stSidebar"] .stMarkdown span {
    color: #1e293b !important;
}
section[data-testid="stSidebar"] hr {
    border-color: #e2e8f0 !important;
}

/* ── Header bar hide ── */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
}

/* ── Tab styling: pill navigation ── */
.stTabs [data-baseweb="tab-list"] {
    background: #f1f5f9 !important;
    border-radius: 999px !important;
    padding: 5px !important;
    gap: 4px !important;
    border: 1px solid #e2e8f0 !important;
    width: fit-content !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 999px !important;
    padding: 8px 22px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    color: #64748b !important;
    border: none !important;
    background: transparent !important;
    white-space: nowrap !important;
}
.stTabs [aria-selected="true"] {
    background: #111827 !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
    display: none !important;
}

/* ── Metric cards ── */
div[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    padding: 20px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
div[data-testid="stMetric"] label {
    color: #64748b !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.03em !important;
}
div[data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-weight: 800 !important;
    font-size: 1.8rem !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 999px !important;
    font-weight: 700 !important;
    padding: 8px 28px !important;
    font-size: 0.88rem !important;
    border: none !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"] {
    background: #111827 !important;
    color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1e293b !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
}

/* ── Selectbox, slider, file uploader ── */
div[data-baseweb="select"] > div {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    color: #0f172a !important;
}
.stSlider > div > div > div {
    color: #0f172a !important;
}

/* ── DataFrame ── */
.stDataFrame {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid #e2e8f0 !important;
}

/* ── Custom components ── */
.brand-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 4px 0 20px 0;
}
.brand-name {
    font-size: 1.6rem;
    font-weight: 900;
    color: #0f172a;
    letter-spacing: -0.5px;
}
.brand-name em {
    font-style: normal;
    color: #3b82f6;
}
.brand-badges {
    display: flex;
    gap: 6px;
    margin-left: auto;
}
.brand-badge {
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    background: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
}

/* ── Hero Section ── */
.hero-section {
    padding: 8px 0 20px 0;
}
.hero-section h1 {
    font-size: 1.9rem !important;
    font-weight: 900 !important;
    color: #0f172a !important;
    letter-spacing: -0.7px !important;
    margin: 0 0 4px 0 !important;
    line-height: 1.15 !important;
}
.hero-subtitle {
    font-size: 0.95rem;
    color: #64748b;
    font-weight: 500;
    margin: 0;
}

/* ── KPI Row ── */
.kpi-row {
    display: flex;
    gap: 28px;
    flex-wrap: wrap;
    padding: 0 0 20px 0;
}
.kpi-item {
    display: flex;
    flex-direction: column;
}
.kpi-label {
    font-size: 0.78rem;
    color: #94a3b8;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 900;
    color: #0f172a;
    letter-spacing: -0.5px;
    line-height: 1.1;
}
.kpi-unit {
    font-size: 0.85rem;
    color: #94a3b8;
    font-weight: 700;
}

/* ── Pipeline Steps ── */
.pipeline {
    display: flex;
    align-items: flex-start;
    gap: 0;
    padding: 12px 0 24px 0;
    overflow-x: auto;
}
.pipe-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    flex: 1;
    min-width: 100px;
    position: relative;
}
.pipe-step::after {
    content: '';
    position: absolute;
    top: 14px;
    left: 50%;
    width: 100%;
    height: 2px;
    background: #e2e8f0;
    z-index: 0;
}
.pipe-step:last-child::after {
    display: none;
}
.pipe-step.done::after {
    background: #22c55e;
}
.pipe-dot {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    font-weight: 800;
    z-index: 1;
    margin-bottom: 6px;
    border: 2px solid #cbd5e1;
    background: #ffffff;
    color: #94a3b8;
}
.pipe-dot.done {
    background: #22c55e;
    border-color: #22c55e;
    color: #ffffff;
}
.pipe-dot.active {
    background: #111827;
    border-color: #111827;
    color: #ffffff;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.2);
}
.pipe-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #64748b;
    line-height: 1.2;
    max-width: 90px;
}

/* ── Dark Feature Card ── */
.dark-card {
    background: #111827;
    border-radius: 16px;
    padding: 24px;
    color: #ffffff;
}
.dark-card h3 {
    font-size: 1.15rem;
    font-weight: 800;
    margin: 0 0 4px 0;
    color: #ffffff;
}
.dark-card .subtitle {
    font-size: 0.82rem;
    color: #94a3b8;
    margin: 0 0 16px 0;
}
.dot-grid {
    display: grid;
    grid-template-columns: repeat(16, 1fr);
    gap: 5px;
    margin: 12px 0;
}
.dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 1.5px solid #374151;
    background: transparent;
}
.dot.red {
    background: #ef4444;
    border-color: #ef4444;
    box-shadow: 0 0 6px rgba(239,68,68,0.5);
}
.dot.green {
    background: #22c55e;
    border-color: #22c55e;
    box-shadow: 0 0 6px rgba(34,197,94,0.5);
}
.legend-row {
    display: flex;
    gap: 16px;
    font-size: 0.78rem;
    color: #94a3b8;
    margin-bottom: 8px;
}
.legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 4px;
}
.avatars-row {
    display: flex;
    align-items: center;
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid #1e293b;
}
.av {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    font-weight: 700;
    color: #ffffff;
    margin-left: -6px;
    border: 2px solid #111827;
}
.av:first-child { margin-left: 0; }

/* ── Pastel Cards ── */
.pastel-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
}
.pastel {
    border-radius: 16px;
    padding: 20px;
}
.pastel.sage   { background: #ecfdf5; }
.pastel.peach  { background: #fef3c7; }
.pastel.sky    { background: #eff6ff; }
.pastel.slate  { background: #f1f5f9; }
.pastel-title {
    font-size: 0.78rem;
    font-weight: 700;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 10px;
}
.pastel-big {
    font-size: 1.9rem;
    font-weight: 900;
    color: #0f172a;
    letter-spacing: -0.4px;
    line-height: 1;
}
.pastel-sub {
    font-size: 0.78rem;
    color: #64748b;
    font-weight: 600;
    margin-top: 4px;
}

/* ── Section Card Container ── */
.section-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}
.section-card h3 {
    font-size: 1.2rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 4px 0;
}
.section-card .desc {
    font-size: 0.88rem;
    color: #64748b;
    margin: 0 0 16px 0;
}

/* ── Sidebar damage pills ── */
.dmg-pill {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px 12px;
    margin-bottom: 5px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 999px;
    font-size: 0.78rem;
}
.dmg-code {
    font-weight: 800;
    min-width: 30px;
}
.dmg-name {
    color: #475569;
    font-weight: 600;
    text-align: right;
}
</style>
"""


def render_brand_bar() -> str:
    return """
    <div class="brand-bar">
        <span style="font-size: 1.5rem;">🛣️</span>
        <span class="brand-name">Crack<em>Map</em></span>
        <div class="brand-badges">
            <span class="brand-badge">Nature MI 2025</span>
            <span class="brand-badge">PyTorch 2.11</span>
            <span class="brand-badge">GPS Ready</span>
        </div>
    </div>
    """


def render_hero(title: str, subtitle: str) -> str:
    return f"""
    <div class="hero-section">
        <h1>{title}</h1>
        <p class="hero-subtitle">{subtitle}</p>
    </div>
    """


def render_kpi_row(metrics: list) -> str:
    """metrics: list of (label, value, unit)"""
    items = ""
    for label, value, unit in metrics:
        items += f"""
        <div class="kpi-item">
            <span class="kpi-label">{label}</span>
            <span class="kpi-value">{value}<span class="kpi-unit"> {unit}</span></span>
        </div>
        """
    return f'<div class="kpi-row">{items}</div>'


def render_pipeline(active: int = 3) -> str:
    steps = [
        "Capture Footage",
        "Road Masking",
        "AI Detection",
        "Severity Score",
        "Dispatch Report"
    ]
    html = ""
    for i, s in enumerate(steps):
        n = i + 1
        if n < active:
            dot_cls = "done"
            step_cls = "done"
            content = "✓"
        elif n == active:
            dot_cls = "active"
            step_cls = "done"
            content = "●"
        else:
            dot_cls = ""
            step_cls = ""
            content = str(n)
        html += f"""
        <div class="pipe-step {step_cls}">
            <div class="pipe-dot {dot_cls}">{content}</div>
            <div class="pipe-label">{s}</div>
        </div>
        """
    return f'<div class="pipeline">{html}</div>'


def render_dark_card(potholes: int = 6, cracks: int = 12, total: int = 64) -> str:
    dots = ""
    for i in range(total):
        if i < potholes:
            dots += '<div class="dot red"></div>'
        elif i < potholes + cracks:
            dots += '<div class="dot green"></div>'
        else:
            dots += '<div class="dot"></div>'

    return f"""
    <div class="dark-card">
        <h3>Pavement Defect Matrix</h3>
        <p class="subtitle">Real-time crowdsensed road anomalies</p>
        <div class="legend-row">
            <span><span class="legend-dot" style="background:#ef4444;"></span> Critical Potholes</span>
            <span><span class="legend-dot" style="background:#22c55e;"></span> Structural Cracks</span>
        </div>
        <div class="dot-grid">{dots}</div>
        <div class="avatars-row">
            <div class="av" style="background:#3b82f6;">TK</div>
            <div class="av" style="background:#8b5cf6;">AD</div>
            <div class="av" style="background:#ec4899;">CB</div>
            <div class="av" style="background:#10b981;">SM</div>
            <div class="av" style="background:#475569; font-size:0.6rem;">+7</div>
            <span style="margin-left:auto; font-size:0.75rem; color:#94a3b8; font-weight:600;">Municipal Squads</span>
        </div>
    </div>
    """


def render_pastel_cards(pci: int, latency: float, top_type: str, coverage: int) -> str:
    return f"""
    <div class="pastel-grid">
        <div class="pastel sage">
            <div class="pastel-title">Pavement Quality</div>
            <div class="pastel-big">{pci}<span class="kpi-unit">/100</span></div>
            <div class="pastel-sub" style="color:#16a34a;">🟢 Routine Level</div>
        </div>
        <div class="pastel peach">
            <div class="pastel-title">Top Defect Type</div>
            <div class="pastel-big" style="font-size:1.4rem;">{top_type}</div>
            <div class="pastel-sub" style="color:#d97706;">⚠️ High Impact</div>
        </div>
        <div class="pastel sky">
            <div class="pastel-title">Inference Speed</div>
            <div class="pastel-big">{latency:.1f}<span class="kpi-unit"> ms</span></div>
            <div class="pastel-sub" style="color:#2563eb;">⚡ Real-time</div>
        </div>
        <div class="pastel slate">
            <div class="pastel-title">Survey Coverage</div>
            <div class="pastel-big">{coverage}<span class="kpi-unit"> govs</span></div>
            <div class="pastel-sub">Tokyo Metro Grid</div>
        </div>
    </div>
    """


def generate_simulated_gps_damage_data(num_points: int = 60, center_lat: float = 35.6762, center_lon: float = 139.6503) -> pd.DataFrame:
    np.random.seed(42)
    records = []
    classes = list(DAMAGE_CLASSES.keys())
    municipalities = ["Adachi", "Chiba", "Ichihara", "Muroran", "Nagakute", "Numazu", "Sumida"]

    for i in range(num_points):
        cls_name = np.random.choice(classes, p=[0.25, 0.1, 0.2, 0.05, 0.2, 0.15, 0.03, 0.02])
        cls_info = DAMAGE_CLASSES[cls_name]
        lat = center_lat + np.random.normal(0, 0.035)
        lon = center_lon + np.random.normal(0, 0.045)
        conf = float(np.random.uniform(0.65, 0.98))
        muni = np.random.choice(municipalities)
        r, g, b = cls_info["rgb"]
        records.append({
            "id": f"DMG-{i+1:04d}",
            "damage_code": cls_name,
            "damage_type": cls_info["name"],
            "category": cls_info["category"],
            "severity": cls_info["severity"],
            "severity_score": cls_info["severity_score"],
            "confidence": round(conf, 2),
            "municipality": muni,
            "lat": lat,
            "lon": lon,
            "color_r": r,
            "color_g": g,
            "color_b": b,
            "color_hex": cls_info["color"],
        })
    return pd.DataFrame(records)


def build_pydeck_map(df: pd.DataFrame, view_mode: str = "Scatter") -> pdk.Deck:
    if df.empty:
        center_lat, center_lon = 35.6762, 139.6503
    else:
        center_lat = float(df["lat"].mean())
        center_lon = float(df["lon"].mean())

    layers = []
    if view_mode in ["Scatter", "Both"]:
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=["lon", "lat"],
            get_color="[color_r, color_g, color_b, 220]",
            get_radius="severity_score * 45 + 60",
            pickable=True,
            auto_highlight=True,
        ))
    if view_mode in ["Heatmap", "Both"]:
        layers.append(pdk.Layer(
            "HeatmapLayer",
            data=df,
            get_position=["lon", "lat"],
            get_weight="severity_score",
            radius_pixels=60,
            intensity=1.6,
            threshold=0.1,
        ))

    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=11.5,
            pitch=25,
        ),
        map_style="mapbox://styles/mapbox/light-v10",
        tooltip={
            "html": "<div style='font-family:Inter,sans-serif;padding:8px;'>"
                    "<b style='color:#3b82f6;'>{damage_code}</b>: {damage_type}<br/>"
                    "<b>Severity:</b> {severity} ({severity_score}/5)<br/>"
                    "<b>Municipality:</b> {municipality}</div>",
            "style": {"background": "#111827", "color": "#ffffff", "borderRadius": "8px"}
        }
    )
