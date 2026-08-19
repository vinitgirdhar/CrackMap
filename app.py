"""
CrackMap — Executive Road Health Intelligence Platform.
Clean enterprise design: light canvas, pill nav, pastel cards, dark feature panels.
"""

import os
import time
from pathlib import Path
import streamlit as st
import numpy as np
import pandas as pd
from PIL import Image
import cv2

from src.config import DAMAGE_CLASSES, CLASS_NAMES, SAMPLES_DIR, DATA_DIR, MODELS_DIR
from src.dataset import (
    parse_voc_dataset_dir,
    draw_bounding_boxes,
    plot_damage_statistics,
    voc_to_yolo,
    voc_to_coco,
    create_sample_dataset,
    BoundingBox,
)
from src.models import (
    RoadDamageInferenceEngine,
    AdvancedRoadDamageDetector,
    build_road_damage_detector,
    train_road_damage_model,
    evaluate_detector,
)
from src.ui_components import (
    MODERN_CSS,
    render_brand_bar,
    render_hero,
    render_kpi_row,
    render_pipeline,
    render_dark_card,
    render_pastel_cards,
    generate_simulated_gps_damage_data,
    build_pydeck_map,
)

# ── Page Config ──
st.set_page_config(
    page_title="CrackMap — Road Health Intelligence",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject CSS
st.markdown(MODERN_CSS, unsafe_allow_html=True)

# Ensure sample data
if not (SAMPLES_DIR / "JPEGImages").exists():
    create_sample_dataset(SAMPLES_DIR, num_samples=12)


# ── Cached model loaders ──
@st.cache_resource(show_spinner=False)
def get_advanced_detector(device: str = "auto"):
    return AdvancedRoadDamageDetector(device=device)


@st.cache_resource(show_spinner=False)
def get_pytorch_engine(arch: str, conf: float, device: str = "cpu"):
    return RoadDamageInferenceEngine(
        architecture=arch, confidence_threshold=conf, device=device
    )


# ═══════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Inspection Engine")

    engine_choice = st.selectbox(
        "AI Detection Architecture",
        [
            "Ensemble (YOLOv8 + ExG Road Saliency)",
            "Pretrained YOLOv8 Neural Net",
            "ExG Road Surface Analyzer",
            "PyTorch Faster R-CNN MobileNet",
        ],
    )

    device_choice = st.selectbox("Compute Hardware", ["cpu", "cuda"])

    conf_threshold = st.slider(
        "Confidence Threshold", 0.10, 0.90, 0.25, 0.05
    )

    st.markdown("---")
    st.markdown("### 🏷️ Damage Taxonomy (JRA)")
    for code, info in DAMAGE_CLASSES.items():
        st.markdown(
            f'<div class="dmg-pill">'
            f'<span class="dmg-code" style="color:{info["color"]};">{code}</span>'
            f'<span class="dmg-name">{info["name"].split("(")[0].strip()}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════
# BRAND BAR
# ═══════════════════════════════════════════
st.markdown(render_brand_bar(), unsafe_allow_html=True)


# ═══════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════
tab_detect, tab_gis, tab_data, tab_train = st.tabs(
    ["🔍 AI Damage Detector", "🗺️ CrackMap GIS", "📊 Dataset & Analytics", "⚡ Train & Benchmark"]
)


# ═══════════════════════════════════════════
# TAB 1 — AI Damage Detector
# ═══════════════════════════════════════════
with tab_detect:
    # Hero + KPIs
    st.markdown(
        render_hero(
            "Road Health Intelligence",
            "AI Pavement Damage Inspection & Crowdsensed GIS Mapping (IEEE BigData Cup / JRA Standards)",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        render_kpi_row([
            ("Roadways Monitored", "148", "km"),
            ("Pavement Health", "78", "/100"),
            ("Active Hazards", "18", "pts"),
            ("Municipalities", "7", "govs"),
        ]),
        unsafe_allow_html=True,
    )

    # Pipeline
    st.markdown(render_pipeline(active=3), unsafe_allow_html=True)

    # Dashboard: dark card + pastel grid
    col_left, col_right = st.columns([1.15, 0.85])
    with col_left:
        st.markdown(render_dark_card(6, 12, 64), unsafe_allow_html=True)
    with col_right:
        st.markdown(render_pastel_cards(78, 16.8, "D40 Pothole", 7), unsafe_allow_html=True)

    st.markdown("")  # spacer

    # ── Inspection Workspace ──
    st.markdown(
        '<div class="section-card">'
        "<h3>📸 Live Road Inspection Studio</h3>"
        '<p class="desc">Upload road photos — the AI segments asphalt pavement and detects genuine potholes and cracks.</p>',
        unsafe_allow_html=True,
    )

    input_mode = st.radio(
        "Source",
        ["Upload Image", "Benchmark Samples", "Dashcam Video"],
        horizontal=True,
        label_visibility="collapsed",
    )

    img = None
    name = ""

    if input_mode == "Upload Image":
        f = st.file_uploader("Road image", type=["jpg", "jpeg", "png", "webp"])
        if f:
            img = Image.open(f).convert("RGB")
            name = f.name

    elif input_mode == "Benchmark Samples":
        samples = sorted((SAMPLES_DIR / "JPEGImages").glob("*.jpg"))
        names = [s.name for s in samples]
        if names:
            sel = st.selectbox("Sample", names)
            img = Image.open(SAMPLES_DIR / "JPEGImages" / sel).convert("RGB")
            name = sel

    else:  # video
        vid = st.file_uploader("Video", type=["mp4", "avi", "mov"])
        if vid:
            tmp = SAMPLES_DIR / "temp_video.mp4"
            tmp.write_bytes(vid.read())
            st.video(str(tmp))

    if img is not None:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Original Road View**")
            st.image(img, use_container_width=True, caption=name)

        with c2:
            st.markdown("**🎯 Detected Potholes & Cracks**")
            with st.spinner("Analyzing road surface…"):
                if "Faster R-CNN" in engine_choice:
                    eng = get_pytorch_engine("fasterrcnn_mobilenet", conf_threshold, device_choice)
                    result = eng.predict(img, custom_conf_threshold=conf_threshold)
                else:
                    eng = get_advanced_detector(device_choice)
                    result = eng.predict(img, custom_conf_threshold=conf_threshold, engine_mode=engine_choice)

                boxes = result.boxes
                st.image(
                    result.image,
                    use_container_width=True,
                    caption=f"{result.inference_time_ms:.0f} ms · {len(boxes)} defects found",
                )

        if boxes:
            st.markdown("#### 📋 Defect Inventory")
            rows = []
            for i, b in enumerate(boxes):
                info = DAMAGE_CLASSES.get(b.name, {})
                rows.append({
                    "#": i + 1,
                    "Code": b.name,
                    "Damage": info.get("name", "?"),
                    "Severity": info.get("severity", "?"),
                    "Confidence": f"{(b.confidence or 1) * 100:.0f}%",
                    "Box": f"[{b.xmin},{b.ymin},{b.xmax},{b.ymax}]",
                    "Area px²": b.area,
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# TAB 2 — GIS CrackMap
# ═══════════════════════════════════════════
with tab_gis:
    st.markdown(
        '<div class="section-card">'
        "<h3>🗺️ Municipal CrackMap & Heatmap</h3>"
        '<p class="desc">Interactive geotagged pavement defects across municipal road networks.</p>',
        unsafe_allow_html=True,
    )

    g1, g2, g3 = st.columns(3)
    with g1:
        view_mode = st.selectbox("Layer", ["Both", "Scatter", "Heatmap"])
    with g2:
        sel_muni = st.selectbox("Municipality", ["All", "Adachi", "Chiba", "Ichihara", "Muroran", "Nagakute", "Numazu", "Sumida"])
    with g3:
        sel_sev = st.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low"])

    df = generate_simulated_gps_damage_data(80)
    if sel_muni != "All":
        df = df[df["municipality"] == sel_muni]
    if sel_sev != "All":
        df = df[df["severity"] == sel_sev]

    st.pydeck_chart(build_pydeck_map(df, view_mode), use_container_width=True)

    st.markdown("#### 🏛️ Municipal Leaderboard")
    full = generate_simulated_gps_damage_data(100)
    agg = full.groupby("municipality").agg(
        Defects=("id", "count"),
        Potholes=("damage_code", lambda s: (s == "D40").sum()),
        Cracks=("damage_code", lambda s: (s == "D20").sum()),
        Avg_Severity=("severity_score", "mean"),
    ).reset_index()
    agg["Avg_Severity"] = agg["Avg_Severity"].round(2)
    agg["Health Score"] = (100 - agg["Avg_Severity"] * 14).astype(int)
    agg = agg.sort_values("Health Score")
    st.dataframe(agg.rename(columns={"municipality": "Municipality"}), use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# TAB 3 — Dataset & Analytics
# ═══════════════════════════════════════════
with tab_data:
    st.markdown(
        '<div class="section-card">'
        "<h3>📊 Dataset Profiler & Format Converter</h3>"
        '<p class="desc">Inspect PASCAL VOC annotations, class balance, and export to YOLO / COCO.</p>',
        unsafe_allow_html=True,
    )

    stats = parse_voc_dataset_dir(SAMPLES_DIR)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Images", stats["total_images"])
    m2.metric("Damaged", stats["damaged_images"])
    m3.metric("Undamaged", stats["undamaged_images"])
    m4.metric("Total Defects", stats["total_boxes"])

    st.markdown("#### 📈 Class Distribution")
    fig = plot_damage_statistics(stats["class_distribution"], title="Road Damage Class Distribution")
    st.pyplot(fig)

    st.markdown("---")
    st.markdown("#### 🔄 Format Converters")
    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("Export to YOLO (.txt)"):
            n = voc_to_yolo(SAMPLES_DIR / "Annotations", SAMPLES_DIR / "YOLO_Annotations")
            st.success(f"Converted {n} annotations")
    with cc2:
        if st.button("Export to COCO (.json)"):
            out = SAMPLES_DIR / "coco_annotations.json"
            r = voc_to_coco(SAMPLES_DIR / "Annotations", out)
            st.success(f"Saved {len(r['annotations'])} objects")

    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════
# TAB 4 — Train & Benchmark
# ═══════════════════════════════════════════
with tab_train:
    st.markdown(
        '<div class="section-card">'
        "<h3>⚡ Fine-Tune on Custom Pothole Images</h3>"
        '<p class="desc">Upload your road photos to fine-tune the neural network for your pavement conditions.</p>',
        unsafe_allow_html=True,
    )

    batch = st.file_uploader(
        "Upload pothole images", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True
    )
    custom_dir = DATA_DIR / "custom_potholes"

    if batch:
        st.success(f"{len(batch)} images selected")
        img_dir = custom_dir / "JPEGImages"
        ann_dir = custom_dir / "Annotations"
        img_dir.mkdir(parents=True, exist_ok=True)
        ann_dir.mkdir(parents=True, exist_ok=True)

        if st.button("📥 Save & Auto-Annotate"):
            with st.spinner("Auto-annotating…"):
                det = get_advanced_detector(device_choice)
                for uf in batch:
                    pil = Image.open(uf).convert("RGB")
                    arr = np.array(pil)
                    pil.save(img_dir / uf.name)
                    res = det.predict(arr, custom_conf_threshold=0.20)
                    bxs = [{"name": b.name, "xmin": b.xmin, "ymin": b.ymin, "xmax": b.xmax, "ymax": b.ymax} for b in res.boxes]
                    from src.dataset.downloader import save_voc_xml
                    save_voc_xml(uf.name, arr.shape[1], arr.shape[0], bxs, ann_dir / (Path(uf.name).stem + ".xml"))
                st.success(f"Annotated {len(batch)} images → `{custom_dir}`")

    st.markdown("---")
    tc1, tc2 = st.columns(2)

    with tc1:
        st.markdown("#### 🛠️ Training Configuration")
        ds_path = st.selectbox("Dataset", [str(custom_dir) if custom_dir.exists() else str(SAMPLES_DIR), str(SAMPLES_DIR)])
        epochs = st.slider("Epochs", 1, 30, 5)
        bs = st.selectbox("Batch Size", [2, 4, 8, 16], index=1)
        lr = st.select_slider("Learning Rate", [0.0005, 0.001, 0.005, 0.01], value=0.005)
        arch = st.selectbox("Backbone", ["fasterrcnn_mobilenet", "ssdlite_mobilenet"])

        if st.button("🚀 Start Training Run", type="primary"):
            bar = st.progress(0)
            status = st.empty()
            chart = st.empty()
            losses = []

            def cb(ep, loss, tot):
                bar.progress(ep / tot)
                status.markdown(f"**Epoch {ep}/{tot}** — Loss: `{loss:.4f}`")
                losses.append(loss)
                chart.line_chart(pd.DataFrame({"Epoch": range(1, len(losses)+1), "Loss": losses}).set_index("Epoch"))

            with st.spinner("Training…"):
                try:
                    tr = train_road_damage_model(
                        dataset_dir=ds_path, architecture=arch, num_epochs=epochs,
                        batch_size=bs, learning_rate=lr,
                        output_checkpoint_name="custom_detector.pth", progress_callback=cb,
                    )
                    st.success(f"Done! Saved → `{tr['checkpoint_path']}`")
                except Exception as e:
                    st.error(str(e))

    with tc2:
        st.markdown("#### 🏆 Benchmark Evaluator (mAP)")
        st.markdown("Evaluate detector on benchmark data using VOC IoU criteria.")
        eval_conf = st.slider("Eval Threshold", 0.1, 0.8, 0.25, key="ev")

        if st.button("📊 Run Evaluation"):
            with st.spinner("Computing mAP@0.5…"):
                ev_eng = get_pytorch_engine(arch, eval_conf, device_choice)
                ev = evaluate_detector(SAMPLES_DIR, ev_eng, confidence_threshold=eval_conf)
                st.metric("mAP@0.5", f"{ev['mAP_50']*100:.1f}%")
                rows = []
                for c, m in ev["class_metrics"].items():
                    rows.append({
                        "Class": c, "Name": DAMAGE_CLASSES.get(c, {}).get("name", c),
                        "Precision": f"{m['precision']*100:.1f}%", "Recall": f"{m['recall']*100:.1f}%",
                        "F1": f"{m['f1']*100:.1f}%", "AP": f"{m['ap']*100:.1f}%", "N": m["support"],
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)
