"""
app.py — NEXUS+ AI Detector v6.0
Cyber forensics UI (violet · cyan · dark glass)
"""

import sys
import os
import base64
from io import BytesIO

import streamlit as st
from PIL import Image

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.detector import full_image_analysis  # noqa: E402

st.set_page_config(
    page_title="NEXUS+ AI Detector",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Neutral gray theme — low saturation, purple upload accent only
BG = "#242424"
PRIMARY = "#525252"
SECONDARY = "#404040"
ACCENT_BLUE = "#6b7280"
ACCENT_CYAN = "#9ca3af"
SUCCESS = "#a3a3a3"
DANGER = "#737373"
WARNING = "#8a8a8a"
GLASS = "rgba(255, 255, 255, 0.07)"
GLASS_BORDER = "rgba(255, 255, 255, 0.14)"
GLASS_BLUR = "blur(22px) saturate(140%)"
GLOW = "rgba(0,0,0,0.35)"
MUTED = "#9ca3af"
SURFACE = "#2e2e2e"
SURFACE_RAISED = "#383838"
BORDER = "#404040"
TEXT = "#d1d5db"
UPLOAD_DASH = "rgba(124, 107, 158, 0.55)"
TINT_VIOLET = "rgba(124, 107, 158, 0.12)"
TINT_CYAN = "rgba(94, 196, 196, 0.08)"
TINT_BLUE = "rgba(100, 130, 180, 0.07)"

_BASE = os.path.dirname(os.path.abspath(__file__))


def _image_to_b64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


with open(os.path.join(_BASE, "style.css"), encoding="utf-8") as f:
    css_content = f.read()
with open(os.path.join(_BASE, "design-system.css"), encoding="utf-8") as f:
    ds_css = f.read()

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

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
    --text: {TEXT};
    --surface: {SURFACE};
    --surface-raised: {SURFACE_RAISED};
    --border: {BORDER};
    --upload-dash: {UPLOAD_DASH};
    --tint-violet: {TINT_VIOLET};
    --tint-cyan: {TINT_CYAN};
    --tint-blue: {TINT_BLUE};
}}
{css_content}
{ds_css}
</style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <div class="glass-bg" aria-hidden="true">
        <div class="glass-orb glass-orb-1"></div>
        <div class="glass-orb glass-orb-2"></div>
        <div class="glass-orb glass-orb-3"></div>
        <div class="natural-light natural-light-main"></div>
        <div class="natural-light natural-light-fill"></div>
        <div class="color-tint color-tint-violet"></div>
        <div class="color-tint color-tint-cyan"></div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="noise-overlay"></div>', unsafe_allow_html=True)
st.markdown('<div class="light-shade" aria-hidden="true"></div>', unsafe_allow_html=True)


# ──────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────

if "page" not in st.session_state:
    st.session_state.page = "landing"       # landing | execute | engines | results
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "result" not in st.session_state:
    st.session_state.result = None
if "scan_image" not in st.session_state:
    st.session_state.scan_image = None
if "scan_meta" not in st.session_state:
    st.session_state.scan_meta = None
if "scan_ready" not in st.session_state:
    st.session_state.scan_ready = False
if "execute_had_file" not in st.session_state:
    st.session_state.execute_had_file = False

# migrate older session key
if st.session_state.page == "home":
    st.session_state.page = "execute"


def _has_live_scan() -> bool:
    """True when an image is uploaded and a scan result is available."""
    return (
        st.session_state.scan_ready
        and st.session_state.result is not None
        and st.session_state.scan_image is not None
    )


def _clear_scan_state(clear_upload: bool = False):
    """Drop upload + scan results from session."""
    st.session_state.result = None
    st.session_state.scan_image = None
    st.session_state.scan_meta = None
    st.session_state.scan_ready = False
    st.session_state.execute_had_file = False
    if clear_upload:
        st.session_state.uploader_key += 1



def _render_engine_grid(result: dict):
    """13-engine score cards from a completed scan."""
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
        s = eng["score"]
        mx = eng["max"]
        pct = (s / mx * 100) if mx > 0 else 0
        ai_pct_eng = pct
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
                    <span class="engine-name">{eng['name']}</span>
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


ENGINES_INFO = [
    {
        "num": "01",
        "name": "Neural Network Ensemble",
        "tag": "HuggingFace Classifiers",
        "summary": "Runs multiple pretrained HuggingFace vision classifiers on your image. Each model votes AI vs. real; NEXUS+ blends those votes into a single neural consensus score for the final verdict.",
    },
    {
        "num": "02",
        "name": "CLIP Semantic Analysis",
        "tag": "OpenAI Zero-Shot",
        "summary": "Uses OpenAI CLIP to compare the image against semantic “AI photo” vs. “real camera photo” prompts without extra training. Catches synthetic scenes and renders that look plausible but aren’t from a camera.",
    },
    {
        "num": "03",
        "name": "Texture Smoothness Analysis",
        "tag": "Multi-Scale Micro-Variance",
        "summary": "Measures fine texture variance across scales. Diffusion portraits often have unnaturally smooth skin and fabric—this engine flags missing organic grain typical of real sensors.",
    },
    {
        "num": "04",
        "name": "Color & Saturation Forensics",
        "tag": "Saturation Distribution",
        "summary": "Inspects hue and saturation histograms for hyper-saturated palettes and flat color bands. Generative pipelines often push neon tones that differ from natural camera color response.",
    },
    {
        "num": "05",
        "name": "Frequency Domain (FFT)",
        "tag": "Fourier Energy Spectrum",
        "summary": "Transforms the image into frequency space to inspect high-frequency energy. Real photos retain sensor noise; AI images often lack it or show grid-like upscaling artifacts.",
    },
    {
        "num": "06",
        "name": "Background & Edge Analysis",
        "tag": "Studio Uniformity",
        "summary": "Checks background blur, edge sharpness, and depth-of-field consistency. Synthetic headshots frequently use fake bokeh or cut-out edges that don’t match optical physics.",
    },
    {
        "num": "07",
        "name": "Portrait Style Analysis",
        "tag": "Composition & Framing",
        "summary": "Evaluates framing, pose, and stylistic templates common in AI headshots and influencer renders. Helps spot stock-AI composition patterns real candid photos rarely match.",
    },
    {
        "num": "08",
        "name": "Gemini / Groq Vision Forensics",
        "tag": "Multimodal API Analysis",
        "summary": "Sends the image to a vision LLM (Gemini or Groq) for qualitative review of lighting, anatomy, and scene logic. Adds human-like reasoning where pixel-only checks can miss subtle flaws.",
    },
    {
        "num": "09",
        "name": "Face Symmetry & Micro-Texture",
        "tag": "Facial Landmark & Blur",
        "summary": "Analyzes facial symmetry, pore-level texture, and landmark spacing. GAN and diffusion faces often show waxy skin, uneven eyes, or overly perfect symmetry.",
    },
    {
        "num": "10",
        "name": "Error Level Analysis (ELA)",
        "tag": "JPEG Compression Residual",
        "summary": "Recompresses the JPEG and maps compression error residuals. Tampered regions, double saves, or inconsistent re-encoding stand out compared with untouched camera files.",
    },
    {
        "num": "11",
        "name": "Fine-Tuned ViT Classifier",
        "tag": "Local Dataset Trained Model",
        "summary": "A Vision Transformer trained on confirmed real and AI portraits from this project’s dataset. Weighted heavily when active—it targets hyperrealistic AI faces that fool generic public models.",
    },
    {
        "num": "12",
        "name": "Watermark Detection",
        "tag": "Margin Text & Logo Search",
        "summary": "Scans margins and corners for generator watermarks, logos, or embedded text left by tools like Midjourney or DALL·E. A direct provenance signal when visible marks remain.",
    },
    {
        "num": "13",
        "name": "ChatGPT / Gemini Provenance",
        "tag": "Generator-Family Compatibility",
        "summary": "Matches visual fingerprints against known generator families (Stable Diffusion, SDXL, DALL·E, etc.). Helps attribute likely source model family, not just AI vs. human.",
    },
]


def _render_engine_catalog():
    """Clickable list of all 13 engines — tap any row for a short summary."""
    st.markdown(
        '<p class="engine-catalog-hint">Click any engine to see what it uses and how it helps detection.</p>',
        unsafe_allow_html=True,
    )
    rows = "".join(
        f'<details class="engine-details">'
        f'<summary class="engine-details-summary">'
        f'<span class="engine-num">{eng["num"]}</span>'
        f'<span class="engine-list-name">{eng["name"]}</span>'
        f'<span class="engine-list-sub">{eng["tag"]}</span>'
        f'<span class="engine-details-chevron">▸</span>'
        f"</summary>"
        f'<p class="engine-detail-body">{eng["summary"]}</p>'
        f"</details>"
        for eng in ENGINES_INFO
    )
    st.markdown(
        f'<div class="glass-card engine-list-wrap">{rows}</div>',
        unsafe_allow_html=True,
    )


def _render_page_subheader(tagline: str, pills: list[str], live: bool = False):
    """Tagline + pill status bar under page title."""
    pill_html = ""
    for i, pill in enumerate(pills):
        if i > 0:
            pill_html += '<span class="scan-header-sep">·</span>'
        if live and i == 0:
            pill_html += (
                f'<span class="scan-header-pill scan-header-pill-live">'
                f'<span class="pulse-dot"></span>{pill}</span>'
            )
        else:
            pill_html += f'<span class="scan-header-pill">{pill}</span>'

    st.markdown(
        f'<div class="scan-page-subheader">'
        f'<p class="scan-header-tagline">{tagline}</p>'
        f'<div class="scan-header-bar">{pill_html}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _results_summary_html(verdict: str, ai_pct: float, human_pct: float) -> str:
    if verdict == "AI-GENERATED":
        return (
            f'<span class="summary-highlight-ai">High AI likelihood detected ({ai_pct:.1f}% AI)</span><br><br>'
            "This image displays strong artificial characteristics across multiple forensic domains. "
            "Primary indicators include anomalous frequency distribution, over-smooth texture variance, "
            "and hyper-saturated color profiles typical of neural diffusion models."
        )
    if verdict == "UNCERTAIN":
        return (
            f'<span class="summary-highlight-unc">Mixed / uncertain analysis ({ai_pct:.1f}% AI)</span><br><br>'
            "The image presents borderline characteristics. Some engines detected natural noise and organic "
            "texture, while others flagged smooth frequency distributions or potential upscaling artifacts."
        )
    return (
        f'<span class="summary-highlight-ok">Authentic human image ({human_pct:.1f}% human)</span><br><br>'
        "The forensic scan confirms natural camera characteristics — organic sensor noise, authentic "
        "frequency variation, natural asymmetry, and no detectable diffusion artifacts."
    )


def _render_top_verdict_note() -> str:
    """Footer line under engine chips — verdict after scan, hint before."""
    if not _has_live_scan():
        return (
            '<div class="engines-lock-note">'
            "Open execution page · upload image · run scan for live scores"
            "</div>"
        )

    result = st.session_state.result
    verdict = result.get("verdict", "")
    ai_pct = float(result.get("confidence_score", 0))
    human_pct = float(result.get("human_score", 100.0 - ai_pct))

    if verdict == "AI-GENERATED":
        cls, label, detail = "top-verdict-ai", "AI GENERATED", f"{ai_pct:.1f}% AI threat"
    elif verdict == "UNCERTAIN":
        cls, label, detail = "top-verdict-unc", "UNCERTAIN", f"{ai_pct:.1f}% AI · {human_pct:.1f}% human"
    else:
        cls, label, detail = "top-verdict-human", "HUMAN", f"{human_pct:.1f}% authentic"

    return (
        f'<div class="top-verdict-bar {cls}">'
        f'<span class="top-verdict-label">Verdict · {label}</span>'
        f'<span class="top-verdict-detail">{detail}</span>'
        f"</div>"
    )


def _nav_to_homepage():
    """HOMEPAGE always opens the landing screen."""
    st.session_state.page = "landing"


def _render_nav():
    """Engines strip + HOMEPAGE · EXECUTION · ENGINES nav."""
    page = st.session_state.page
    home_active = page == "landing"
    exec_active = page == "execute"
    eng_active = page == "engines"

    chips = "".join(
        f'<span class="top-engine-chip">{eng["name"]}</span>'
        for eng in ENGINES_INFO
    )
    footer_note = "" if page == "execute" else _render_top_verdict_note()

    if page == "execute":
        st.markdown(
            '<div class="top-header-wrap"><div class="top-engines-bar top-engines-bar-execute">'
            '<div class="top-engines-hero">NEXUS+ <span class="version-badge">v6.0</span></div>'
            "</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="top-header-wrap"><div class="top-engines-bar">'
            f'<div class="top-engines-label">Engines</div>'
            f'<div class="top-engine-strip">{chips}</div>{footer_note}'
            f"</div></div>",
            unsafe_allow_html=True,
        )

    home_active_css = (
        "border-color: #d1d5db !important; "
        "box-shadow: inset 0 1px 0 rgba(209,213,219,0.28), inset 0 -2px 0 rgba(0,0,0,0.22), "
        "0 6px 22px rgba(0,0,0,0.45), 0 0 28px rgba(209,213,219,0.14) !important;"
        if home_active else ""
    )
    exec_active_css = (
        "border-color: #d1d5db !important; "
        "box-shadow: inset 0 1px 0 rgba(209,213,219,0.28), inset 0 -2px 0 rgba(0,0,0,0.22), "
        "0 6px 22px rgba(0,0,0,0.45), 0 0 28px rgba(209,213,219,0.14) !important;"
        if exec_active else ""
    )
    eng_active_css = (
        "border-color: #d1d5db !important; "
        "box-shadow: inset 0 1px 0 rgba(209,213,219,0.28), inset 0 -2px 0 rgba(0,0,0,0.22), "
        "0 6px 22px rgba(0,0,0,0.45), 0 0 28px rgba(209,213,219,0.14) !important;"
        if eng_active else ""
    )
    st.markdown(
        f"""
        <style>
        .top-header-wrap + div[data-testid="stHorizontalBlock"]
            [data-testid="column"]:nth-child(2)
            [data-testid="stHorizontalBlock"]
            [data-testid="column"]:nth-child(1) .stButton > button {{
            {home_active_css}
        }}
        .top-header-wrap + div[data-testid="stHorizontalBlock"]
            [data-testid="column"]:nth-child(2)
            [data-testid="stHorizontalBlock"]
            [data-testid="column"]:nth-child(2) .stButton > button {{
            {exec_active_css}
        }}
        .top-header-wrap + div[data-testid="stHorizontalBlock"]
            [data-testid="column"]:nth-child(2)
            [data-testid="stHorizontalBlock"]
            [data-testid="column"]:nth-child(3) .stButton > button {{
            {eng_active_css}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, nav_col, _ = st.columns([1, 3.4, 1])
    with nav_col:
        n1, n2, n3 = st.columns(3, gap="small")
        with n1:
            if st.button(
                "HOMEPAGE",
                key="nav_home",
                use_container_width=True,
                type="primary",
            ):
                _nav_to_homepage()
                st.rerun()
        with n2:
            if st.button(
                "EXECUTION",
                key="nav_execute",
                use_container_width=True,
                type="primary",
            ):
                st.session_state.page = "execute"
                st.rerun()
        with n3:
            if st.button(
                "ENGINES",
                key="nav_engines",
                use_container_width=True,
                type="primary",
            ):
                st.session_state.page = "engines"
                st.rerun()


_render_nav()


def _go_execution(clear_upload: bool = True):
    """Reset to execution page. Optionally clears the uploaded file too."""
    st.session_state.page = "execute"
    _clear_scan_state(clear_upload=clear_upload)


def _render_execution_header():
    """Page header for the execution / upload screen."""
    _render_page_subheader(
        "Upload image payload · run 13-engine scan",
        ["System ready", "13 engines armed", "PNG · JPG · WEBP"],
        live=True,
    )


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
# LANDING PAGE
# ──────────────────────────────────────────────

if st.session_state.page == "landing":
    st.markdown(
        """
        <div class="landing-page page-fade">
        <h1 class="landing-hero">NEXUS+ <span class="version-badge">v6.0</span></h1>
        <p class="landing-tagline">13-engine AI image forensics · deep multi-domain inspection</p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class="landing-features">
        <div class="landing-feature"><span class="lf-num">13</span><span class="lf-label">Detection engines</span></div>
        <div class="landing-feature"><span class="lf-num">FFT</span><span class="lf-label">Frequency analysis</span></div>
        <div class="landing-feature"><span class="lf-num">ViT</span><span class="lf-label">Fine-tuned classifier</span></div>
        <div class="landing-feature"><span class="lf-num">CLIP</span><span class="lf-label">Semantic forensics</span></div>
    </div>
    """, unsafe_allow_html=True)

    _, cta_col, _ = st.columns([1, 1.2, 1])
    with cta_col:
        if st.button("Begin Forensic Scan", use_container_width=True, type="primary"):
            st.session_state.page = "execute"
            st.rerun()

    st.markdown(
        """
        <div class="landing-note glass-card">
            <div class="glass-title">Platform</div>
            <p class="landing-copy">
                Upload a profile or media image to run a full forensic sweep across neural, spectral,
                texture, and provenance engines. Results include human vs AI breakdown and per-engine scores.
            </p>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
# ENGINES PAGE
# ══════════════════════════════════════════════════════════════

elif st.session_state.page == "engines":
    st.markdown(
        "<h1>Detection <span class='version-badge'>Engines</span></h1>",
        unsafe_allow_html=True,
    )
    _render_page_subheader(
        "Forensic modules in every scan",
        ["13 modules", "Neural · Spectral · Provenance"],
    )

    _render_engine_catalog()

    if _has_live_scan():
        result = st.session_state.result
        st.markdown("""
        <div class="section-heading engines-section-heading">
            <span class="sh-icon">🔬</span>
            <span class="sh-text">Live Scan Results</span>
            <span class="sh-line"></span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(
            f"<p class='landing-tagline'>{result['verdict_label']} · "
            f"{result['confidence_score']:.1f}% AI threat · per-engine scores below</p>",
            unsafe_allow_html=True,
        )
        _render_engine_grid(result)

        _, nav_row, _ = st.columns([1, 1.2, 1])
        with nav_row:
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("← Scan summary", use_container_width=True, type="secondary"):
                    st.session_state.page = "results"
                    st.rerun()
            with c2:
                if st.button("New scan", use_container_width=True, type="secondary"):
                    _go_execution(clear_upload=True)
                    st.rerun()
    elif st.session_state.scan_ready:
        _, exec_col, _ = st.columns([1, 1.2, 1])
        with exec_col:
            if st.button("⚡  Execute Forensic Scan", use_container_width=True, type="primary"):
                st.session_state.page = "execute"
                st.rerun()
    else:
        _, exec_col, _ = st.columns([1, 1.2, 1])
        with exec_col:
            if st.button("Go to execution page →", use_container_width=True, type="primary"):
                st.session_state.page = "execute"
                st.rerun()


# ══════════════════════════════════════════════════════════════
# EXECUTION PAGE  (upload + execute)
# ══════════════════════════════════════════════════════════════

elif st.session_state.page == "execute":

    left, mid, right = st.columns([1, 2, 1])
    with mid:
        _render_execution_header()

        # ── Upload Card ──
        st.markdown(
            """
            <div class="upload-card-head glass-card">
                <div class="glass-title">Image Payload</div>
            </div>
            """,
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
            st.session_state.execute_had_file = True
            st.session_state.scan_ready = True
            image = Image.open(uploaded).convert("RGB")
            meta = {
                "width": image.width,
                "height": image.height,
                "fmt": (uploaded.type.split("/")[-1] if getattr(uploaded, "type", None) else "img").upper(),
                "name": uploaded.name,
            }
            _render_image_lightbox(image, meta, toggle_id="exec-img-zoom-toggle")
        elif st.session_state.execute_had_file:
            _clear_scan_state(clear_upload=False)
            st.rerun()

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
                _go_execution(clear_upload=True)
                st.rerun()
        else:
            analyze = False

        chips = "".join(
            f'<span class="engine-chip" style="animation-delay:{i * 0.03:.2f}s">{eng["name"]}</span>'
            for i, eng in enumerate(ENGINES_INFO)
        )
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <div class="glass-title" style="justify-content:center;">13 Detection Engines Ready</div>
            <div class="engine-chip-strip">{chips}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Trigger analysis → jump to scan summary page ──
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
            st.session_state.scan_ready = True
            st.rerun()


# ══════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════

elif st.session_state.page == "results":
    result = st.session_state.result
    image = st.session_state.scan_image
    meta = st.session_state.scan_meta

    if result is None or image is None:
        st.session_state.page = "execute"
        st.rerun()

    st.markdown(
        "<h1 style='font-size:1.9rem !important;'>NEXUS+ "
        "<span class='version-badge' style='font-size:1rem;'>v6.0 · SCAN RESULTS</span></h1>",
        unsafe_allow_html=True,
    )

    # ── Back / New Scan control ──
    back_col, _spacer = st.columns([1, 4])
    with back_col:
        new_scan = st.button("←  New Scan", type="secondary", use_container_width=True)
    if new_scan:
        _go_execution(clear_upload=True)
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
        st.markdown(
            """
            <div class="glass-card result-thumb-card">
            <div class="glass-title">Analyzed Image</div>
            """,
            unsafe_allow_html=True,
        )
        _render_image_lightbox(image, meta, toggle_id="results-img-zoom-toggle")
        st.markdown(
            f"""
            <div class="result-meta-row">
                <span>{meta['width']}×{meta['height']}px</span>
                <span>{meta['fmt']}</span>
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

    st.markdown(
        f"""
        <div class="glass-card">
        <div class="glass-title">Forensic Summary</div>
        <div class="summary-text">{_results_summary_html(verdict, ai_pct, human_pct)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, eng_cta, _ = st.columns([1, 1.2, 1])
    with eng_cta:
        if st.button("View 13-engine breakdown →", use_container_width=True, type="primary"):
            st.session_state.page = "engines"
            st.rerun()


# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────

st.markdown(
    '<div class="footer-text">NEXUS+ <span>·</span> AI Detector v6.0 <span>·</span> '
    '13-Engine Multi-Domain Forensics <span>·</span> '
    'HuggingFace + OpenAI CLIP + FFT</div>',
    unsafe_allow_html=True,
)
