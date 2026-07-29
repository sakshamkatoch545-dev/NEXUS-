"""
app.py — NEXUS+ AI Detector v6.0
══════════════════════════════════
Glassmorphism Premium Dark UI for AI image forensics.

This build keeps the ORIGINAL detection logic, 13-engine list, and the
Human-vs-AI / 13-Engine-Forensics breakdown completely unchanged. Only the
color palette (now the NEXUS v6.0 violet/cyan theme) and the upload zone
(drag & drop glowing dashed zone, matching the NEXUS v6.0 mock) have been
restyled, plus a matching animated background.
"""

import random
import sys
import os
import base64
from io import BytesIO
from datetime import datetime

import streamlit as st
from PIL import Image
import altair as alt
import numpy as np
from typing import List, Dict, Any

# ── Ensure detector module is importable ──
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# pyrefly: ignore [missing-import]
from src.detector import full_image_analysis  # noqa: E402

# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="NEXUS+ AI Detector",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# NEXUS v6.0 THEME PALETTE (applied to the original layout below)
# ──────────────────────────────────────────────
BG = "#070A18"
PRIMARY = "#8B5CF6"
SECONDARY = "#6D5EFF"
ACCENT_BLUE = "#4F8DFF"
ACCENT_CYAN = "#5EF4FF"
SUCCESS = "#2ED573"
DANGER = "#FF5C8A"
WARNING = "#F6C343"
GLASS = "rgba(255,255,255,.06)"
GLASS_BORDER = "rgba(255,255,255,.12)"
GLOW = "rgba(139,92,246,.35)"
MUTED = "#98A2B3"


def _image_to_b64(img: Image.Image, fmt: str = "PNG") -> str:
    """Encode a PIL image to a base64 string for inline <img> embedding."""
    buf = BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ──────────────────────────────────────────────
# GLASSMORPHISM THEME CSS  (NEXUS v6.0 palette + original layout/typography)
# ──────────────────────────────────────────────

with open('style.css', 'r', encoding='utf-8') as f:
    css_content = f.read()

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700;800&display=swap');

:root {{
    --bg: {BG};
    --primary: {PRIMARY};
    --secondary: {SECONDARY};
    --accent-blue: {ACCENT_BLUE};
    --accent-cyan: {ACCENT_CYAN};
    --success: {SUCCESS};
    --danger: {DANGER};
    --warning: {WARNING};
    --glass: {GLASS};
    --glass-border: {GLASS_BORDER};
    --glow: {GLOW};
    --muted: {MUTED};
}}

{css_content}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# ANIMATED BACKGROUND (NEXUS v6.0 blobs + particles)
# ──────────────────────────────────────────────

_particles_html = "".join(
    f'<div class="particle" style="left:{random.randint(0,100)}%; '
    f'animation-duration:{random.randint(14,26)}s; '
    f'animation-delay:-{random.randint(0,20)}s;"></div>'
    for _ in range(24)
)
st.markdown(
    f"""
    <div class="nexus-bg">
        <div class="aurora-sweep"></div>
        <div class="blob blob-1"></div>
        <div class="blob blob-2"></div>
        <div class="blob blob-3"></div>
        {_particles_html}
    </div>
    <div class="noise-overlay"></div>
    """,
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────
# SESSION STATE — controls which "page" is shown
# ──────────────────────────────────────────────

if "page" not in st.session_state:
    st.session_state.page = "home"          # "home" | "results"
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "result" not in st.session_state:
    st.session_state.result = None
if "scan_image" not in st.session_state:
    st.session_state.scan_image = None
if "scan_meta" not in st.session_state:
    st.session_state.scan_meta = None


def _go_home(clear_upload: bool = True):
    """Reset to the homepage. Optionally clears the uploaded file too."""
    st.session_state.page = "home"
    st.session_state.result = None
    st.session_state.scan_image = None
    st.session_state.scan_meta = None
    if clear_upload:
        st.session_state.uploader_key += 1


ENGINES_INFO = [
    ("01", "Neural Network Ensemble", "HuggingFace Classifiers"),
    ("02", "CLIP Semantic Analysis", "OpenAI Zero-Shot"),
    ("03", "Texture Smoothness", "Multi-Scale Micro-Variance"),
    ("04", "Color & Saturation", "Saturation Distribution"),
    ("05", "Frequency Domain FFT", "Fourier Energy Spectrum"),
    ("06", "Background & Edge", "Studio Uniformity"),
    ("07", "Portrait Style", "Composition & Framing"),
    ("08", "Gemini / Groq Vision Forensics", "Multimodal API Analysis"),
    ("09", "Face Symmetry & Smoothness", "Facial Landmark & Blur"),
    ("10", "Error Level Analysis (ELA)", "JPEG Compression Residual"),
    ("11", "Fine-Tuned ViT Classifier", "Local Dataset Trained Model"),
    ("12", "Watermark Detection", "Margin Text & Logo Search"),
    ("13", "ChatGPT / Gemini Provenance", "Generator-Family Compatibility"),
]


def _render_image_lightbox(image: Image.Image, meta: dict, toggle_id: str):
    """Click-to-zoom full-resolution preview, reused on both pages."""
    img_b64 = _image_to_b64(image)
    st.markdown(f"""
    <div class="img-preview-wrap">
        <input type="checkbox" id="{toggle_id}" class="img-zoom-toggle">
        <label for="{toggle_id}" class="img-preview-trigger">
            <img src="data:image/png;base64,{img_b64}" class="preview-thumb" />
            <div class="img-preview-hint">🔍 Click for full-resolution preview</div>
        </label>
        <label for="{toggle_id}" class="img-zoom-overlay">
            <img src="data:image/png;base64,{img_b64}" class="img-zoom-full" onclick="event.stopPropagation();" />
            <div class="img-zoom-meta">{meta['width']} × {meta['height']}px · {meta['fmt']} · {meta['name']}</div>
            <div class="img-zoom-close-hint">click anywhere to close</div>
        </label>
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# HEADER  (title shrinks slightly once on the results page)
# ──────────────────────────────────────────────

if st.session_state.page == "home":
    st.markdown(
        "<h1>NEXUS+ <span class='version-badge'>v6.0</span></h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='subtitle'>Artificial · Intelligence · Forensics // Deep 13-Engine Inspection</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<h1 style='font-size:1.9rem !important;'>NEXUS+ "
        "<span class='version-badge' style='font-size:1rem;'>v6.0 · SCAN RESULTS</span></h1>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
# PAGE 1 — HOME  (upload + execute, nothing else)
# ══════════════════════════════════════════════════════════════

if st.session_state.page == "home":

    left, mid, right = st.columns([1, 2, 1])
    with mid:
        st.markdown('<div class="page-fade">', unsafe_allow_html=True)

        # ── Upload Card ──
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="glass-title">Image Payload</div>',
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "Drop image for forensic scan",
            type=["png", "jpg", "jpeg", "webp"],
            label_visibility="collapsed",
            key=f"uploader_{st.session_state.uploader_key}",
        )

        image = None
        if uploaded:
            image = Image.open(uploaded).convert("RGB")
            meta = {
                "width": image.width,
                "height": image.height,
                "fmt": (uploaded.type.split("/")[-1] if getattr(uploaded, "type", None) else "img").upper(),
                "name": uploaded.name,
            }
            _render_image_lightbox(image, meta, toggle_id="home-img-zoom-toggle")

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Execute / Cancel controls ──
        if uploaded:
            c1, c2 = st.columns([2.2, 1])
            with c1:
                analyze = st.button(
                    "⚡  Execute Forensic Scan",
                    use_container_width=True,
                    type="primary",
                )
            with c2:
                cancel = st.button(
                    "✕  Cancel",
                    use_container_width=True,
                    type="secondary",
                )
            if cancel:
                _go_home(clear_upload=True)
                st.rerun()
        else:
            analyze = st.button(
                "⚡  Execute Forensic Scan",
                use_container_width=True,
                type="primary",
                disabled=True,
            )

        # ── Engine teaser chips ──
        chips = "".join(
            f'<span class="engine-chip" style="animation-delay:{i*0.03:.2f}s">{name}</span>'
            for i, (_n, name, _s) in enumerate(ENGINES_INFO)
        )
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <div class="glass-title" style="justify-content:center;">13 Detection Engines Ready</div>
            <div class="engine-chip-strip">{chips}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)  # .page-fade

        # ── Trigger analysis → jump to results page ──
        if analyze and uploaded and image is not None:
            with st.spinner(""):
                st.markdown(
                    "<div class='scan-pulse' style='text-align:center;'>"
                    "[ Forensic Scan In Progress — 13 Engines Active ]</div>",
                    unsafe_allow_html=True,
                )
                result = full_image_analysis(image)

            st.session_state.result = result
            st.session_state.scan_image = image
            st.session_state.scan_meta = {
                "width": image.width,
                "height": image.height,
                "fmt": (uploaded.type.split("/")[-1] if getattr(uploaded, "type", None) else "img").upper(),
                "name": uploaded.name,
            }
            st.session_state.page = "results"
            st.rerun()


# ══════════════════════════════════════════════════════════════
    # PAGE 2 — RESULTS  (Human vs AI breakdown + 13-Engine forensics, together)
# ══════════════════════════════════════════════════════════════

else:
    result = st.session_state.result
    image = st.session_state.scan_image
    meta = st.session_state.scan_meta

    if result is None or image is None:
        # safety net — nothing to show, bounce back home
        _go_home(clear_upload=False)
        st.rerun()

    st.markdown('<div class="page-fade">', unsafe_allow_html=True)

    # ── Back / New Scan control ──
    st.markdown('<div class="back-btn-wrap">', unsafe_allow_html=True)
    back_col, _spacer = st.columns([1, 4])
    with back_col:
        new_scan = st.button("←  New Scan", type="secondary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if new_scan:
        _go_home(clear_upload=True)
        st.rerun()

    score   = result["confidence_score"]
    verdict = result["verdict"]

    if verdict == "AI-GENERATED":
        vc, fc = "v-ai", "fill-ai"
    elif verdict == "UNCERTAIN":
        vc, fc = "v-unc", "fill-unc"
    else:
        vc, fc = "v-real", "fill-real"

    ai_pct      = score
    human_pct   = result.get("human_score", 100.0 - score)
    ai_votes    = result.get("high_risk_engine_count", 0)
    human_votes = result.get("human_engine_count", 0)

    # ══════════════════════════════════════════════
    # SECTION 1 — ANALYZED IMAGE + VERDICT
    # ══════════════════════════════════════════════
    img_col, verdict_col = st.columns([1, 1.6], gap="large")

    with img_col:
        st.markdown('<div class="glass-card result-thumb-card">', unsafe_allow_html=True)
        st.markdown('<div class="glass-title">Analyzed Image</div>', unsafe_allow_html=True)
        _render_image_lightbox(image, meta, toggle_id="results-img-zoom-toggle")
        st.markdown(f"""
        <div class="result-meta-row">
            <span>{meta['width']}×{meta['height']}px</span>
            <span>{meta['fmt']}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with verdict_col:
        st.markdown(f"""
        <div class="verdict-box {vc}">
            <h2>{result["verdict_label"]}</h2>
            <div class="v-score">
                AI Threat Score
                <span>{score:.1f}</span>
                / 100
            </div>
            <div class="verdict-bar">
                <div class="verdict-fill {fc}" style="width:{min(score, 100):.1f}%"></div>
            </div>
            <div style="margin-top:0.8rem;font-family:'JetBrains Mono',monospace;font-size:0.72rem;
                color:rgba(226,232,240,.72);letter-spacing:0.06em;">
                13-ENGINE AVERAGE: {ai_pct:.1f}% AI · {human_pct:.1f}% HUMAN
                <span style="opacity:0.65;">({ai_votes} HIGH-RISK · {human_votes} LOWER-RISK)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Metric Cards ──
    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card m-human">
            <div class="m-label">Human Confidence</div>
            <div class="m-value">{human_pct:.1f}%</div>
        </div>
        <div class="metric-card m-ai">
            <div class="m-label">AI Probability</div>
            <div class="m-value">{ai_pct:.1f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Summary Card ──
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="glass-title">Forensic Summary</div>', unsafe_allow_html=True)

    if verdict == "AI-GENERATED":
        st.markdown(f"""
        <div class="summary-text">
            <span class="summary-highlight-ai">🚨 High AI Likelihood Detected ({ai_pct:.1f}% AI)</span><br><br>
            This image displays strong artificial characteristics across multiple forensic domains.
            Primary indicators include anomalous frequency distribution, over-smooth texture variance,
            and hyper-saturated color profiles typical of neural diffusion models such as SDXL,
            Midjourney, or Stable Diffusion.
        </div>
        """, unsafe_allow_html=True)
    elif verdict == "UNCERTAIN":
        st.markdown(f"""
        <div class="summary-text">
            <span class="summary-highlight-unc">⚠️ Mixed / Uncertain Analysis ({ai_pct:.1f}% AI)</span><br><br>
            The image presents borderline characteristics. Some engines detected natural
            noise and organic texture, while others flagged smooth frequency distributions
            or potential upscaling artifacts. Manual review is recommended.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="summary-text">
            <span class="summary-highlight-ok">✅ Authentic Human Image Confirmed ({human_pct:.1f}% Human)</span><br><br>
            The forensic scan confirms natural camera characteristics. The image presents
            organic sensor noise, authentic frequency variation, natural asymmetry,
            and no detectable steganographic watermarks or diffusion artifacts.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # SECTION 2 — 13-ENGINE FORENSICS (same page, below breakdown)
    # ══════════════════════════════════════════════
    st.markdown("""
    <div class="section-heading">
        <span class="sh-icon">🔬</span>
        <span class="sh-text">13-Engine Forensics</span>
        <span class="sh-line"></span>
    </div>
    """, unsafe_allow_html=True)

    eng_col1, eng_col2 = st.columns(2, gap="medium")
    eng_columns = [eng_col1, eng_col2]

    for idx, (_key, eng) in enumerate(result["engines"].items()):
        s   = eng["score"]
        mx  = eng["max"]
        pct = (s / mx * 100) if mx > 0 else 0

        ai_pct_eng    = pct
        human_pct_eng = 100.0 - pct

        if pct > 60:
            badge_cls, fill_cls, badge_txt = "badge-high", "efill-hi", "HIGH AI RISK"
        elif pct > 30:
            badge_cls, fill_cls, badge_txt = "badge-mod", "efill-mod", "MODERATE"
        else:
            badge_cls, fill_cls, badge_txt = "badge-low", "efill-lo", "LOW AI RISK"

        with eng_columns[idx % 2]:
            st.markdown(f"""
            <div class="engine-card" style="animation-delay:{(idx % 6) * 0.06:.2f}s">
                <div class="engine-header">
                    <span class="engine-icon">{eng['icon']}</span>
                    <span class="engine-name">{eng['name']}</span>
                    <span class="engine-cog">⚙</span>
                    <span class="engine-badge {badge_cls}">{badge_txt}</span>
                </div>
                <div class="engine-score-block">
                    <div class="engine-score-main">
                        <span class="engine-val">{s:.0f}</span>
                        <span class="engine-max">/{mx}</span>
                    </div>
                    <div class="engine-pct-sub">{ai_pct_eng:.0f}% AI &nbsp;/&nbsp; {human_pct_eng:.0f}% HUMAN</div>
                </div>
                <div class="engine-bar">
                    <div class="engine-fill {fill_cls}" style="width:{pct:.1f}%"></div>
                </div>
                <div class="engine-explain">{eng['explanation']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # .page-fade


# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────

st.markdown(
    '<div class="footer-text">NEXUS+ <span>·</span> AI Detector v6.0 <span>·</span> '
    '13-Engine Multi-Domain Forensics <span>·</span> '
    'HuggingFace + OpenAI CLIP + FFT</div>',
    unsafe_allow_html=True,
)
