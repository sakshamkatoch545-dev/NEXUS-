import sys
import os
import textwrap
import base64
import threading
from io import BytesIO

import streamlit as st
from PIL import Image

_BASE = os.path.dirname(os.path.abspath(__file__))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

try:
    from src.detector import (
        full_image_analysis,
        warmup_models,
        extract_image_forensic_specs,
        match_image_against_registry,
        learn_and_register_image,
        _get_cached_registry,
    )
except Exception:
    import importlib.util
    _spec_d = importlib.util.spec_from_file_location("detector", os.path.join(_BASE, "src", "detector.py"))
    _mod_d = importlib.util.module_from_spec(_spec_d)
    _spec_d.loader.exec_module(_mod_d)
    full_image_analysis = _mod_d.full_image_analysis
    warmup_models = _mod_d.warmup_models
    extract_image_forensic_specs = _mod_d.extract_image_forensic_specs
    match_image_against_registry = _mod_d.match_image_against_registry
    learn_and_register_image = _mod_d.learn_and_register_image
    _get_cached_registry = _mod_d._get_cached_registry

try:
    from src.auth import (
        is_authenticated,
        get_current_user,
        login_user,
        logout_user,
        get_google_auth_url,
        exchange_google_code,
        verify_google_id_token,
        verify_credentials,
        login_demo_google_user,
        try_restore_session_from_token,
    )
except Exception:
    import importlib.util
    _spec_a = importlib.util.spec_from_file_location("auth", os.path.join(_BASE, "src", "auth.py"))
    _mod_a = importlib.util.module_from_spec(_spec_a)
    _spec_a.loader.exec_module(_mod_a)
    is_authenticated = _mod_a.is_authenticated
    get_current_user = _mod_a.get_current_user
    login_user = _mod_a.login_user
    logout_user = _mod_a.logout_user
    get_google_auth_url = _mod_a.get_google_auth_url
    exchange_google_code = _mod_a.exchange_google_code
    verify_google_id_token = _mod_a.verify_google_id_token
    verify_credentials = _mod_a.verify_credentials
    login_demo_google_user = _mod_a.login_demo_google_user
    try_restore_session_from_token = _mod_a.try_restore_session_from_token

def _render_html(html_str: str):
    """Render pure HTML safely via native st.html without Markdown parser interference."""
    st.html(textwrap.dedent(html_str).strip())

# Background Zero-Latency Model Warmup
if "warmed_up" not in st.session_state:
    st.session_state.warmed_up = True
    threading.Thread(target=warmup_models, daemon=True).start()

st.set_page_config(
    page_title="NEXUS+ AI Detector",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 30-DAY PERSISTENT SESSION AUTO-RESTORE ──
if "session_token" in st.query_params and not is_authenticated():
    s_token = st.query_params.get("session_token")
    if try_restore_session_from_token(s_token):
        st.query_params.clear()
        st.rerun()
    else:
        st.query_params.clear()

# ── GOOGLE OAUTH 2.0 / 2-STEP VERIFICATION CALLBACK ──
if "code" in st.query_params:
    auth_code = st.query_params.get("code")
    if auth_code:
        user_info = exchange_google_code(auth_code)
        if user_info:
            login_user({
                "name": user_info.get("name", "Google User"),
                "email": user_info.get("email", ""),
                "role": "GOOGLE 2-STEP VERIFIED",
                "auth_type": "google",
                "avatar": user_info.get("picture", ""),
            }, remember_30_days=True)
            st.query_params.clear()
            st.rerun()

if "id_token" in st.query_params:
    id_tok = st.query_params.get("id_token")
    if id_tok:
        user_info = verify_google_id_token(id_tok)
        if user_info:
            login_user(user_info, remember_30_days=True)
            st.query_params.clear()
            st.rerun()

# ── LOCALSTORAGE 30-DAY SYNC JAVASCRIPT BRIDGE ──
if st.session_state.get("new_login_token"):
    t_val = st.session_state.new_login_token
    st.session_state.new_login_token = None
    _render_html(f"""
    <script>
    try {{
        localStorage.setItem('nexus_auth_token', '{t_val}');
    }} catch(e) {{}}
    </script>
    """)
elif st.session_state.get("logout_signal"):
    st.session_state.logout_signal = None
    _render_html("""
    <script>
    try {{
        localStorage.removeItem('nexus_auth_token');
        const p = new URLSearchParams(window.location.search);
        if (p.has('session_token')) {{
            p.delete('session_token');
            history.replaceState(null, '', window.location.pathname);
        }}
    }} catch(e) {{}}
    </script>
    """)
elif not is_authenticated():
    # Attempt auto-login from browser LocalStorage
    _render_html("""
    <script>
    (function() {
        try {
            const token = localStorage.getItem('nexus_auth_token');
            const params = new URLSearchParams(window.location.search);
            if (token && !params.has('session_token') && !window.__nexus_auth_checked) {
                window.__nexus_auth_checked = true;
                params.set('session_token', token);
                window.location.search = params.toString();
            }
        } catch(e) {}
    })();
    </script>
    """)

# Theme Factory — Cyberpunk Multi-Spectrum Obsidian Palette
BG = "#080c14"
PRIMARY = "#8b5cf6"
SECONDARY = "#1e1b4b"
ACCENT_BLUE = "#3b82f6"
ACCENT_CYAN = "#06b6d4"
ACCENT_MAGENTA = "#d946ef"
ACCENT_AMBER = "#f59e0b"
ACCENT_EMERALD = "#10b981"
SUCCESS = "#10b981"
DANGER = "#ef4444"
WARNING = "#f59e0b"
GLASS = "rgba(15, 23, 42, 0.75)"
GLASS_BORDER = "rgba(217, 70, 239, 0.25)"
GLASS_BLUR = "blur(12px)"
GLOW = "rgba(217, 70, 239, 0.35)"
MUTED = "#cbd5e1"
SURFACE = "#111827"
SURFACE_RAISED = "#1f2937"
BORDER = "rgba(139, 92, 246, 0.22)"
TEXT = "#ffffff"
UPLOAD_DASH = "rgba(217, 70, 239, 0.6)"
TINT_VIOLET = "rgba(139, 92, 246, 0.18)"
TINT_CYAN = "rgba(6, 182, 212, 0.15)"
TINT_MAGENTA = "rgba(217, 70, 239, 0.18)"
TINT_AMBER = "rgba(245, 158, 11, 0.14)"

_BASE = os.path.dirname(os.path.abspath(__file__))


@st.cache_data(show_spinner=False, max_entries=32)
def _image_bytes_to_b64(img_bytes: bytes, fmt: str = "JPEG") -> str:
    img = Image.open(BytesIO(img_bytes))
    buf = BytesIO()
    working_img = img.copy()
    working_img.thumbnail((600, 600), Image.Resampling.BILINEAR)
    if working_img.mode != "RGB":
        working_img = working_img.convert("RGB")
    working_img.save(buf, format=fmt, quality=75, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _image_to_b64(img: Image.Image, fmt: str = "JPEG") -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return _image_bytes_to_b64(buf.getvalue(), fmt=fmt)

def _read_css_files():
    with open(os.path.join(_BASE, "style.css"), encoding="utf-8") as f:
        css_content = f.read()
    with open(os.path.join(_BASE, "design-system.css"), encoding="utf-8") as f:
        ds_css = f.read()
    return css_content, ds_css

css_content, ds_css = _read_css_files()

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

:root {{
    --bg: {BG};
    --primary: {PRIMARY};
    --secondary: {SECONDARY};
    --accent-blue: {ACCENT_BLUE};
    --accent-cyan: {ACCENT_CYAN};
    --accent-magenta: {ACCENT_MAGENTA};
    --accent-amber: {ACCENT_AMBER};
    --accent-emerald: {ACCENT_EMERALD};
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
    --tint-magenta: {TINT_MAGENTA};
    --tint-amber: {TINT_AMBER};
}}

/* ── Large Primary Action Button ── */
button[kind="primary"], [data-testid="stBaseButton-primary"] {{
    min-height: 4.5rem !important;
    font-size: 1.25rem !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase;
    border-radius: 12px !important;
    background: linear-gradient(135deg, var(--primary) 0%, var(--accent-magenta) 100%) !important;
    border: none !important;
    box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3) !important;
    transition: all 0.3s ease !important;
}}
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 40px rgba(217, 70, 239, 0.4) !important;
    filter: brightness(1.1) !important;
}}
button[kind="primary"] p, [data-testid="stBaseButton-primary"] p {{
    font-size: 1.25rem !important;
    font-weight: 700 !important;
}}

/* ── Engine Grid Layout ── */
.engine-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
    margin-bottom: 2rem;
}}
.engine-grid .engine-card {{
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between;
}}

/* ── AI-EDITED / Inpainting Cyber Styling ── */
.v-edited {{
    border-color: rgba(245, 158, 11, 0.45) !important;
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.14) 0%, rgba(15, 23, 42, 0.75) 100%) !important;
    box-shadow: 0 0 35px rgba(245, 158, 11, 0.25) !important;
}}
.v-edited h2 {{ color: #f59e0b !important; text-shadow: 0 0 16px rgba(245, 158, 11, 0.4) !important; }}
.fill-edited {{ background: linear-gradient(90deg, #f59e0b, #d97706) !important; }}
.top-verdict-edited {{
    background: rgba(245, 158, 11, 0.14) !important;
    border: 1px solid rgba(245, 158, 11, 0.35) !important;
    color: #fbbf24 !important;
}}
.m-edited {{ border-left-color: #f59e0b !important; }}
.m-edited .m-label, .m-edited .m-value {{ color: #fbbf24 !important; }}

{css_content}
{ds_css}
</style>
""", unsafe_allow_html=True)

_render_html('<div class="glass-bg-optimized" aria-hidden="true"></div>')


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
    """14-engine score cards from a completed scan."""
    html_cards = []
    for idx, (key, eng) in enumerate(result["engines"].items()):
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

        icon = ""
        is_judge = (key == "forensic_judge")
        judge_style = "border: 1px solid rgba(6,182,212,0.5); background: linear-gradient(135deg, rgba(15,23,42,0.92) 0%, rgba(6,182,212,0.08) 100%);" if is_judge else ""
        card_html = (
            f'<div class="engine-card" style="animation-delay:{(idx % 6) * 0.06:.2f}s; {judge_style}">'
            f'<div class="engine-header">'
            f'<span class="engine-name">{icon} {eng["name"]}</span>'
            f'<span class="engine-badge {badge_cls}">{badge_txt}</span>'
            f'</div>'
            f'<div class="engine-score-block">'
            f'<div class="engine-score-main">'
            f'<span class="engine-val">{s:.0f}</span>'
            f'<span class="engine-max">/{mx}</span>'
            f'</div>'
            f'<div class="engine-pct-sub">{ai_pct_eng:.0f}% AI &nbsp;/&nbsp; {human_pct_eng:.0f}% HUMAN</div>'
            f'</div>'
            f'<div class="engine-bar">'
            f'<div class="engine-fill {fill_cls}" style="width:{pct:.1f}%"></div>'
            f'</div>'
            f'<div class="engine-explain">{eng["explanation"]}</div>'
            f'</div>'
        )
        html_cards.append(card_html)

    grid_html = (
        '<div class="section-heading">'
        '<span class="sh-icon">[CONSENSUS]</span>'
        '<span class="sh-text">14-Engine Multi-Domain Forensics</span>'
        '<span class="sh-line"></span>'
        '</div>'
        f'<div class="engine-grid">{"".join(html_cards)}</div>'
    )
    _render_html(grid_html)


ENGINES_INFO = [
    {
        "num": "01",
        "name": "Neural Network Ensemble",
        "tag": "ViT / ResNet Classifier",
        "summary": "Deep vision backbone extracting multi-layer representations to detect spatial and latent diffusion fingerprints across synthesized imagery.",
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
        "name": "Face Symmetry & Micro-Texture",
        "tag": "Facial Landmark & Blur",
        "summary": "Analyzes facial symmetry, pore-level texture, and landmark spacing. GAN and diffusion faces often show waxy skin, uneven eyes, or overly perfect symmetry.",
    },
    {
        "num": "09",
        "name": "Error Level Analysis (ELA)",
        "tag": "JPEG Compression Residual",
        "summary": "Recompresses the JPEG and maps compression error residuals. Tampered regions, double saves, or inconsistent re-encoding stand out compared with untouched camera files.",
    },
    {
        "num": "10",
        "name": "Fine-Tuned ViT Classifier",
        "tag": "Local Dataset Trained Model",
        "summary": "A Vision Transformer trained on confirmed real and AI portraits from this project’s dataset. Weighted heavily when active—it targets hyperrealistic AI faces that fool generic public models.",
    },
    {
        "num": "11",
        "name": "Watermark Detection",
        "tag": "Margin Text & Logo Search",
        "summary": "Scans margins and corners for generator watermarks, logos, or embedded text left by tools like Midjourney or DALL·E. A direct provenance signal when visible marks remain.",
    },
    {
        "num": "12",
        "name": "AI & Generator Provenance",
        "tag": "Generator-Family Compatibility",
        "summary": "Matches visual fingerprints against known generator families (Stable Diffusion, SDXL, Midjourney, DALL·E, etc.). Helps attribute likely source model family, not just AI vs. human.",
    },
    {
        "num": "13",
        "name": "AI Inpainting & Retouch Forensics",
        "tag": "Wavelet Sensor Noise Disparity",
        "summary": "Scans multi-tile spatial grids with Donoho wavelets and texture-normalized ratios. Accurately flags authentic camera photographs that have been partially edited, enhanced, or inpainted by AI.",
    },
    {
        "num": "14",
        "name": "Forensic Judge & Meta-Consensus",
        "tag": "Multi-Domain Judicial Arbitration",
        "summary": "Synthesizes evidence across all neural, spectral, compression, and inpainting domains into a unified Bayesian consensus to maximize detection precision and eliminate borderline ambiguities.",
    },
]


def _render_engine_catalog():
    """Clickable list of all 14 engines — tap any row for a short summary."""
    _render_html('<p class="engine-catalog-hint">Click any engine to see what it uses and how it helps detection.</p>')
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
    _render_html(f'<div class="glass-card engine-list-wrap">{rows}</div>')


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

    _render_html(
        f'<div class="scan-page-subheader">'
        f'<p class="scan-header-tagline">{tagline}</p>'
        f'<div class="scan-header-bar">{pill_html}</div>'
        f"</div>"
    )


def _results_summary_html(verdict: str, ai_pct: float, human_pct: float, edit_pct: float = 0.0) -> str:
    if verdict in ("AI-GENERATED", "GENERATED BY AI"):
        return (
            f'<span class="summary-highlight-ai">Generated by AI ({ai_pct:.1f}% AI threat)</span><br><br>'
            "This image displays strong artificial characteristics across multiple forensic domains. "
            "Primary indicators include anomalous frequency distribution, over-smooth texture variance, "
            "and hyper-saturated color profiles typical of neural diffusion models."
        )
    if verdict == "AI-EDITED":
        return (
            f'<span style="color:#f59e0b;font-weight:700;font-size:1.05rem;">Likely Real Photograph with AI Edits / Retouching Detected</span><br><br>'
            f"Forensic grid analysis confirms this image has a <b>genuine camera capture foundation</b> ({human_pct:.1f}% base authenticity), "
            f"but contains <b>localized AI generative fill, neural retouching, or AI filtering</b> (inconsistency threat: <b>{edit_pct:.1f}%</b>). "
            "Bimodal sensor noise distributions and boundary gradient discontinuities were identified in specific sub-regions."
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

    if verdict in ("AI-GENERATED", "GENERATED BY AI"):
        cls, label, detail = "top-verdict-ai", "GENERATED BY AI", f"{ai_pct:.1f}% AI threat"
    elif verdict == "AI-EDITED":
        cls, label, detail = "top-verdict-edited", "LIKELY REAL BUT EDITED BY AI", f"{ai_pct:.1f}% AI in sub-regions"
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
    """Engines strip + HOMEPAGE · EXECUTION · ENGINES · TRAIN nav."""
    page = st.session_state.page
    home_active = page == "landing"
    exec_active = page == "execute"
    eng_active = page == "engines"
    train_active = page == "train"

    chips = "".join(
        f'<span class="top-engine-chip">{eng["name"]}</span>'
        for eng in ENGINES_INFO
    )
    footer_note = "" if page in ("execute", "train") else _render_top_verdict_note()

    if page == "execute":
        _render_html(
            '<div class="top-header-wrap"><div class="top-engines-bar top-engines-bar-execute">'
            '<div class="top-engines-hero">NEXUS+ <span class="version-badge">v6.0</span></div>'
            "</div></div>"
        )
    elif page == "train":
        _render_html(
            '<div class="top-header-wrap"><div class="top-engines-bar top-engines-bar-execute">'
            '<div class="top-engines-hero">NEXUS+ <span class="version-badge">FORENSIC TRAINER</span></div>'
            "</div></div>"
        )
    else:
        _render_html(
            f'<div class="top-header-wrap"><div class="top-engines-bar">'
            f'<div class="top-engines-label">Engines</div>'
            f'<div class="top-engine-strip">{chips}</div>{footer_note}'
            f"</div></div>"
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
    train_active_css = (
        "border-color: #d1d5db !important; "
        "box-shadow: inset 0 1px 0 rgba(209,213,219,0.28), inset 0 -2px 0 rgba(0,0,0,0.22), "
        "0 6px 22px rgba(0,0,0,0.45), 0 0 28px rgba(209,213,219,0.14) !important;"
        if train_active else ""
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
        .top-header-wrap + div[data-testid="stHorizontalBlock"]
            [data-testid="column"]:nth-child(2)
            [data-testid="stHorizontalBlock"]
            [data-testid="column"]:nth-child(4) .stButton > button {{
            {train_active_css}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # User Profile & Sign Out Bar
    u = get_current_user()
    u_name = u.get("name", "Analyst")
    u_role = u.get("role", "TIER-1 INVESTIGATOR")
    u_email = u.get("email", "")

    _, top_user_bar, _ = st.columns([1, 4.2, 1])
    with top_user_bar:
        u_left, u_right = st.columns([3, 1])
        with u_left:
            _render_html(f"""
            <div style="display:flex; align-items:center; gap:0.6rem; margin-top:0.4rem;">
                <span class="user-nav-badge">
                    <span style="color:#a78bfa;font-weight:700;">{u_name}</span>
                    <span class="user-nav-role">{u_role}</span>
                </span>
            </div>
            """)
        with u_right:
            if st.button("Sign Out", key="top_nav_logout", type="secondary", use_container_width=True):
                logout_user()
                st.rerun()

    _, nav_col, _ = st.columns([1, 4.2, 1])
    with nav_col:
        n1, n2, n3, n4 = st.columns(4, gap="small")
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
        with n4:
            if st.button(
                "TRAIN",
                key="nav_train",
                use_container_width=True,
                type="primary",
            ):
                st.session_state.page = "train"
                st.rerun()


def _render_login_page():
    """Cyberpunk Login and Google 2-Step Authentication Page with 30-Day Persistent Session."""
    from src.auth import save_google_credentials, _load_auth_config

    _render_html("""
    <div class="login-wrapper">
        <div class="login-card">
            <div class="status-badge-wrap" style="margin-bottom:0.8rem;">
                <span class="status-dot"></span>
                <span class="status-text">SECURE 2-STEP FORENSIC PORTAL</span>
            </div>
            <div class="login-header-hero">NEXUS+ <span class="version-badge">v7.0</span></div>
            <div class="login-header-sub">Advanced AI Image Forensics & Meta-Arbitration Platform</div>
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:#10b981; margin-bottom:1.5rem; letter-spacing:0.04em;">
                ENCRYPTED 30-DAY PERSISTENT SESSION AUTO-LOGIN ENABLED
            </div>
        </div>
    </div>
    """)

    _, mid_l, _ = st.columns([1, 1.7, 1])
    with mid_l:
        cfg = _load_auth_config()
        g_url = get_google_auth_url()

        if g_url:
            st.markdown(f'''
            <a href="{g_url}" target="_self" class="google-auth-btn">
                <svg width="22" height="22" viewBox="0 0 24 24" style="margin-right: 6px;">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                <span>Sign in Free with Google</span>
            </a>
            ''', unsafe_allow_html=True)
        else:
            # Custom styled button with Google icon
            _render_html('''
            <div style="margin-bottom: 0.8rem;">
                <div class="google-auth-btn" onclick="document.getElementById('hidden_google_btn').click();" style="cursor: pointer;">
                    <svg width="22" height="22" viewBox="0 0 24 24" style="margin-right: 6px;">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                    </svg>
                    <span>Sign in Free with Google</span>
                </div>
            </div>
            ''')
            if st.button("Connect Google Account", key="hidden_google_btn", type="primary", use_container_width=True):
                st.session_state.show_google_setup = True

        if not g_url and st.session_state.get("show_google_setup", True):
            _render_html("<div style='margin-top: 1rem;'></div>")
            with st.container():
                st.info("Enter your Google Cloud OAuth Client ID & Secret to connect live Google Sign-In:")
                c1, c2 = st.columns(2, gap="small")
                with c1:
                    c_id_in = st.text_input("Google Client ID:", value=cfg.get("client_id", ""), placeholder="xxxx.apps.googleusercontent.com")
                with c2:
                    c_sec_in = st.text_input("Google Client Secret:", value=cfg.get("client_secret", ""), type="password", placeholder="GOCSPX-xxxx")
                if st.button("Activate Google Sign-In", type="primary", use_container_width=True):
                    if c_id_in and c_sec_in:
                        save_google_credentials(c_id_in, c_sec_in)
                        st.success("Google OAuth 2.0 Activated! Refreshing...")
                        st.rerun()
                    else:
                        st.warning("Please provide both Client ID and Client Secret.")

        _render_html("""
        <div class="auth-divider">
            <span>or sign in with analyst credentials</span>
        </div>
        """)

        with st.form("analyst_login_form"):
            email_input = st.text_input("Analyst Identifier / Email:", value="analyst@nexus.forensics")
            pass_input = st.text_input("Passcode:", type="password", value="nexus")
            remember_chk = st.checkbox("Keep me signed in for 30 days on this device", value=True)
            submit_btn = st.form_submit_button("Authenticate & Lock Session", use_container_width=True, type="primary")

            if submit_btn:
                user = verify_credentials(email_input, pass_input)
                if user:
                    login_user(user, remember_30_days=remember_chk)
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please enter a valid email and password.")

        if g_url:
            _render_html("<div style='margin-top: 1.5rem;'></div>")
            with st.expander("Google Cloud OAuth Settings & Credentials"):
                st.markdown(textwrap.dedent("""
                **Connected Google Cloud Web Application:**
                - Redirect URI: `http://localhost:8501`
                - Scopes: `openid email profile`
                - 2-Step Verification: Active
                """))
                c_id = st.text_input("Update Client ID:", value=cfg.get("client_id", ""), type="password")
                c_sec = st.text_input("Update Client Secret:", value=cfg.get("client_secret", ""), type="password")
                if st.button("Update Credentials", type="secondary"):
                    if c_id and c_sec:
                        save_google_credentials(c_id, c_sec)
                        st.success("Credentials updated!")
                        st.rerun()


# ── SESSION AUTHENTICATION GATEKEEPER ──
if not is_authenticated():
    _render_login_page()
    st.stop()

_render_nav()


def _go_execution(clear_upload: bool = True):
    """Reset to execution page. Optionally clears the uploaded file too."""
    st.session_state.page = "execute"
    _clear_scan_state(clear_upload=clear_upload)


def _render_execution_header():
    """Page header for the execution / upload screen."""
    _render_page_subheader(
        "Upload image payload · run 14-engine scan",
        ["System ready", "14 engines armed", "PNG · JPG · WEBP"],
        live=True,
    )


def _render_image_lightbox(image: Image.Image, meta: dict, toggle_id: str, card_title: str = "", show_card: bool = False):
    """Click-to-zoom full-resolution preview, reused on both pages."""
    img_b64 = _image_to_b64(image)
    lightbox_inner = f"""
    <div class="img-preview-wrap">
        <input type="checkbox" id="{toggle_id}" class="img-zoom-toggle">
        <label for="{toggle_id}" class="img-preview-trigger">
            <img src="data:image/jpeg;base64,{img_b64}" class="preview-thumb" />
            <div class="img-preview-hint">Click for full-resolution preview</div>
        </label>
        <label for="{toggle_id}" class="img-zoom-overlay">
            <img src="data:image/jpeg;base64,{img_b64}" class="img-zoom-full" onclick="event.stopPropagation();" />
            <div class="img-zoom-meta">{meta['width']} × {meta['height']}px · {meta['fmt']} · {meta['name']}</div>
            <div class="img-zoom-close-hint">click anywhere to close</div>
        </label>
    </div>
    """
    if show_card:
        title_html = f'<div class="glass-title">{card_title}</div>' if card_title else ""
        meta_html = f"""
        <div class="result-meta-row">
            <span>{meta['width']}×{meta['height']}px</span>
            <span>{meta['fmt']}</span>
        </div>
        """
        full_html = f"""
        <div class="glass-card result-thumb-card">
            {title_html}
            {lightbox_inner}
            {meta_html}
        </div>
        """
        _render_html(full_html)
    else:
        _render_html(lightbox_inner)


# ──────────────────────────────────────────────
# LANDING PAGE
# ──────────────────────────────────────────────

if st.session_state.page == "landing":
    _render_html(
        """
        <div class="liquid-hero-frame landing-page page-fade" style="text-align: center;">
            <div class="status-badge-wrap">
                <span class="status-dot"></span>
                <span class="status-text">14 FORENSIC ENGINES ONLINE</span>
            </div>
            <h1 class="landing-hero">NEXUS+ <span class="version-badge">v7.0</span></h1>
            <p class="landing-tagline"><b>Advanced AI Image Forensics & Meta-Judge</b></p>
            <p class="landing-subtagline">Calibrated for <b>Diffusion Models</b>, <b>GANs</b> & <b>AI Inpainting</b></p>
        </div>
        """
    )

    _render_html("""
    <div class="landing-metrics-bar">
        <div class="l-metric-card">
            <span class="lm-val">14</span>
            <span class="lm-lbl">Detection Engines</span>
        </div>
        <div class="l-metric-card">
            <span class="lm-val">FFT + ELA</span>
            <span class="lm-lbl">Spectral Forensics</span>
        </div>
        <div class="l-metric-card">
            <span class="lm-val">ViT + CLIP</span>
            <span class="lm-lbl">Neural Consensus</span>
        </div>
        <div class="l-metric-card">
            <span class="lm-val">AI Judge</span>
            <span class="lm-lbl">Meta-Arbitration</span>
        </div>
    </div>
    """)

    _render_html("""
    <div class="landing-cta-box">
        <h3 class="cta-title">Ready for Forensic Inspection?</h3>
        <p class="cta-desc">Upload any profile picture, media render, or suspect photo to generate a comprehensive 14-engine threat score breakdown.</p>
    </div>
    """)

    _, cta_col, _ = st.columns([1, 1.3, 1])
    with cta_col:
        if st.button("Begin Forensic Scan", use_container_width=True, type="primary"):
            st.session_state.page = "execute"
            st.rerun()

    _render_html("""
    <div class="landing-pillars-grid">
        <div class="pillar-card">
            <div class="pillar-icon">01</div>
            <div class="pillar-title">Neural & Semantic</div>
            <div class="pillar-desc">Combines fine-tuned Vision Transformers with OpenAI CLIP zero-shot semantic matching to flag synthetic rendering patterns.</div>
        </div>
        <div class="pillar-card">
            <div class="pillar-icon">02</div>
            <div class="pillar-title">Spectral & Frequency</div>
            <div class="pillar-desc">Calculates 2D Fast Fourier Transforms (FFT) and multi-scale texture smoothness to detect high-frequency sensor noise loss.</div>
        </div>
        <div class="pillar-card">
            <div class="pillar-icon">03</div>
            <div class="pillar-title">Compression & Inpainting</div>
            <div class="pillar-desc">Re-compresses JPEG error levels (ELA) and analyzes spatial noise/gradient boundaries to detect localized AI inpainting and generative edits.</div>
        </div>
        <div class="pillar-card">
            <div class="pillar-icon">04</div>
            <div class="pillar-title">Forensic Judge Engine</div>
            <div class="pillar-desc">Meta-ensemble arbitration synthesizes cross-domain signals into a Bayesian consensus to eliminate borderline ambiguity.</div>
        </div>
    </div>
    """)

    chips = "".join(
        f'<span class="engine-chip" style="margin: 0.2rem;">{eng["name"]}</span>'
        for eng in ENGINES_INFO
    )
    _render_html(f"""
    <div class="glass-card" style="text-align:center; margin-top: 1.5rem;">
        <div class="glass-title" style="justify-content:center;">14 Active Forensic Inspection Modules</div>
        <div class="showcase-chip-grid">{chips}</div>
    </div>
    """)


# ══════════════════════════════════════════════════════════════
# ENGINES PAGE
# ══════════════════════════════════════════════════════════════

elif st.session_state.page == "engines":
    _render_html(
        "<h1>Detection <span class='version-badge'>Engines</span></h1>"
    )
    _render_page_subheader(
        "Forensic modules in every scan",
        ["14 modules", "Neural · Spectral · Inpainting · Provenance · Judge"],
    )

    if _has_live_scan():
        result = st.session_state.result
        _render_html(
            f"<p class='landing-tagline'>{result['verdict_label']} · "
            f"{result['confidence_score']:.1f}% AI threat · per-engine scores below</p>"
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

        _render_html(
            '<div class="section-heading" style="margin-top:2.5rem;">'
            '<span class="sh-icon">[SPECS]</span>'
            '<span class="sh-text">Engine Specifications & Architecture</span>'
            '<span class="sh-line"></span>'
            '</div>'
        )
        _render_engine_catalog()
    else:
        _render_engine_catalog()

        if st.session_state.scan_ready:
            _, exec_col, _ = st.columns([1, 1.2, 1])
            with exec_col:
                if st.button("Execute Forensic Scan", use_container_width=True, type="primary"):
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
        _render_html(
            """
            <div class="upload-card-head glass-card">
                <div class="glass-title">Image Payload</div>
            </div>
            """
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
                    "Execute Forensic Scan",
                    use_container_width=True,
                    type="primary",
                )
            with c2:
                cancel = st.button(
                    "Cancel",
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
        _render_html(f"""
        <div class="glass-card" style="text-align:center;">
            <div class="glass-title" style="justify-content:center;">14 Detection Engines Ready</div>
            <div class="engine-chip-strip">{chips}</div>
        </div>
        """)

        # ── Trigger analysis → jump to scan summary page ──
        if analyze and uploaded and image is not None:
            scan_slot = st.empty()
            prog_bar = st.progress(10)
            status_text = st.empty()
            
            def _st_progress(pct: int, label: str):
                prog_bar.progress(min(pct, 100))
                status_text.markdown(
                    f"<div class='scan-pulse' style='text-align:center; font-size:0.95rem; color:#06b6d4;'>"
                    f"[{pct}%] {label}</div>",
                    unsafe_allow_html=True,
                )
            
            _st_progress(20, "Armed 14 forensic & neural engines (including AI Judge & Inpainting)...")
            result = full_image_analysis(image)
            _st_progress(100, "Forensic consensus verified!")

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

    _render_html(
        "<h1 style='font-size:1.9rem !important;'>NEXUS+ "
        "<span class='version-badge' style='font-size:1rem;'>v7.0 · SCAN RESULTS</span></h1>"
    )

    # ── Back / New Scan control ──
    _, back_col, _ = st.columns([1, 1.4, 1])
    with back_col:
        new_scan = st.button("←  New Scan", type="secondary", use_container_width=True)
    if new_scan:
        _go_execution(clear_upload=True)
        st.rerun()

    score   = result["confidence_score"]
    verdict = result["verdict"]
    is_edited = bool(result.get("is_ai_edited", False) and verdict == "AI-EDITED")
    ai_edited_score = float(result.get("ai_edited_score", 0.0))

    if verdict in ("AI-GENERATED", "GENERATED BY AI"):
        vc, fc = "v-ai", "fill-ai"
    elif verdict == "AI-EDITED":
        vc, fc = "v-edited", "fill-edited"
    elif verdict == "UNCERTAIN":
        vc, fc = "v-unc", "fill-unc"
    else:
        vc, fc = "v-real", "fill-real"

    ai_pct      = score
    human_pct   = result.get("human_score", 100.0 - score)
    ai_votes    = result.get("high_risk_engine_count", 0)
    human_votes = result.get("human_engine_count", 0)

    # ── Memory Exemplar Match Banner ──
    if result.get("is_memory_match"):
        mm = result.get("memory_match", {})
        sim_val = result.get("memory_similarity", 100.0)
        ex = mm.get("exemplar", {})
        m_type = mm.get("match_type", "EXEMPLAR_MATCH")
        notes_str = f"<br><b>Exemplar Notes:</b> {ex.get('notes')}" if ex.get('notes') else ""
        _render_html(f"""
        <div class="memory-match-banner">
            <div class="memory-match-title">TRAINED MEMORY MATCH CONFIRMED ({sim_val:.1f}% Similarity)</div>
            <div class="memory-match-sub">
                <b>Matched Exemplar:</b> {ex.get('filename', 'Trained Exemplar')} &nbsp;·&nbsp;
                <b>Match Engine:</b> {m_type} &nbsp;·&nbsp;
                <b>Registered:</b> {ex.get('registered_at', 'N/A')}
                {notes_str}
            </div>
        </div>
        """)

    # ══════════════════════════════════════════════
    # SECTION 1 — ANALYZED IMAGE + VERDICT
    # ══════════════════════════════════════════════
    img_col, verdict_col = st.columns([1, 1.6], gap="large")

    with img_col:
        _render_image_lightbox(
            image,
            meta,
            toggle_id="results-img-zoom-toggle",
            card_title="Analyzed Image",
            show_card=True
        )

    with verdict_col:
        _render_html(f"""
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
                14-ENGINE AVERAGE: {ai_pct:.1f}% AI · {human_pct:.1f}% HUMAN
                <span style="opacity:0.65;">({ai_votes} HIGH-RISK · {human_votes} LOWER-RISK)</span>
            </div>
        </div>
        """)

    # ── Metric Cards ──
    if is_edited or verdict == "AI-EDITED":
        _render_html(f"""
        <div class="metric-grid" style="grid-template-columns: repeat(3, 1fr);">
            <div class="metric-card m-human">
                <div class="m-label">Base Authenticity</div>
                <div class="m-value">{human_pct:.1f}%</div>
            </div>
            <div class="metric-card m-edited">
                <div class="m-label">AI Inpainting Threat</div>
                <div class="m-value">{ai_edited_score:.1f}%</div>
            </div>
            <div class="metric-card m-ai">
                <div class="m-label">Global AI Score</div>
                <div class="m-value">{ai_pct:.1f}%</div>
            </div>
        </div>
        """)
    else:
        _render_html(f"""
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
        """)

    _render_html(f"""
    <div class="glass-card">
    <div class="glass-title">Forensic Summary</div>
    <div class="summary-text">{_results_summary_html(verdict, ai_pct, human_pct, edit_pct=ai_edited_score)}</div>
    </div>
    """)

    _, eng_cta, _ = st.columns([1, 1.2, 1])
    with eng_cta:
        if st.button("View 14-engine breakdown →", use_container_width=True, type="primary"):
            st.session_state.page = "engines"
            st.rerun()


# ══════════════════════════════════════════════════════════════
# TRAIN & MEMORY PAGE
# ══════════════════════════════════════════════════════════════

elif st.session_state.page == "train":
    _render_html(
        "<h1 style='margin-bottom: 0.2rem;'>Forensic <span class='version-badge'>TRAINER & MEMORY BANK</span></h1>"
    )
    _render_page_subheader(
        "Teach & Remember Image Specs · Perceptual Fingerprints · Exemplar Recall",
        ["Spec Extraction", "dHash Fingerprinting", "Instant Spec-Matching"],
    )

    _render_html("<div style='margin-top: 1.5rem;'></div>")

    t_train, t_match, t_bank = st.tabs([
        "Train & Remember Image",
        "Spec-Match Suspect Photo",
        "Learned Knowledge Bank",
    ])

    # ── TAB 1: TRAIN & REMEMBER ──
    with t_train:
        _render_html("<div style='margin-top: 1.2rem;'></div>")
        left_t, mid_t, right_t = st.columns([1, 2.8, 1])
        with mid_t:
            _render_html(
                """
                <div class="upload-card-head glass-card" style="margin-bottom: 1.2rem;">
                    <div class="glass-title">1. Select Training Image Payload</div>
                </div>
                """
            )

            train_file = st.file_uploader(
                "Upload image to teach NEXUS+",
                type=["png", "jpg", "jpeg", "webp"],
                key="trainer_uploader",
                label_visibility="collapsed",
            )

            if train_file:
                train_img = Image.open(train_file).convert("RGB")
                
                # Centered, bounded preview
                p_c1, p_c2, p_c3 = st.columns([1, 2, 1])
                with p_c2:
                    st.image(train_img, use_container_width=True, caption=f"{train_file.name} ({train_img.width}x{train_img.height}px)")

                _render_html("<div style='margin-top: 1.5rem;'></div>")
                _render_html("""
                <div class="glass-card" style="padding: 1.2rem 1.4rem; margin-bottom: 1.2rem;">
                    <div class="glass-title" style="margin-bottom: 0.8rem;">2. Define Ground Truth & Metadata</div>
                </div>
                """)

                label_choice = st.radio(
                    "Ground Truth Classification Category:",
                    [
                        "GENERATED BY AI (Full Synthetic Diffusion / Midjourney / Flux / SDXL)",
                        "AI-EDITED (Authentic Camera Base + AI Inpainting / Filter / Retouch)",
                        "AUTHENTIC / REAL (Original Optical Camera Capture)",
                    ],
                    index=0,
                )

                if "GENERATED" in label_choice:
                    target_label = "generated_by_ai"
                elif "EDITED" in label_choice:
                    target_label = "ai_edited"
                else:
                    target_label = "real"

                _render_html("<div style='margin-top: 1rem;'></div>")
                train_notes = st.text_input(
                    "Exemplar Description / Custom Notes (optional):",
                    placeholder="e.g., Midjourney v6 photorealistic studio portrait or iPhone 15 real portrait",
                )

                _render_html("<div style='margin-top: 1.6rem;'></div>")
                if st.button("Train & Remember Image", type="primary", use_container_width=True):
                    with st.spinner("Extracting 14-engine forensic specs and registering to permanent memory..."):
                        record = learn_and_register_image(train_img, label=target_label, notes=train_notes)
                        st.success(f"Successfully trained and locked {os.path.basename(train_file.name)} in permanent memory!")
                        
                        specs = record.get("forensic_specs", {})
                        h_freq = specs.get('frequency_specs', {}).get('high_frequency_ratio', 0)
                        l_var = specs.get('texture_specs', {}).get('laplacian_variance', 0)
                        n_std = specs.get('noise_specs', {}).get('sensor_noise_std', 0)
                        s_mean = specs.get('color_profile', {}).get('saturation_mean', 0)

                        _render_html(f"""
                        <div class="train-card">
                            <div style="font-size:1.15rem;font-weight:800;color:#10b981;margin-bottom:0.8rem;letter-spacing:0.04em;">
                                LOCKED FORENSIC CERTIFICATE: {record['verdict_label']}
                            </div>
                            <div style="margin-bottom:0.35rem;"><b>SHA-256:</b> <code style="color:#a78bfa;">{record['sha256']}</code></div>
                            <div style="margin-bottom:0.35rem;"><b>Perceptual dHash:</b> <code style="color:#38bdf8;">{record['dhash']}</code></div>
                            <div style="margin-bottom:0.35rem;"><b>Archived Dataset:</b> <code style="color:#94a3b8;">{record['dataset_path']}</code></div>
                            <div class="train-spec-grid">
                                <div class="train-spec-item">
                                    <div class="train-spec-item-label">FFT High-Freq Ratio</div>
                                    <div class="train-spec-item-val">{h_freq}</div>
                                </div>
                                <div class="train-spec-item">
                                    <div class="train-spec-item-label">Texture Laplacian Var</div>
                                    <div class="train-spec-item-val">{l_var}</div>
                                </div>
                                <div class="train-spec-item">
                                    <div class="train-spec-item-label">Sensor Noise STD</div>
                                    <div class="train-spec-item-val">{n_std}</div>
                                </div>
                                <div class="train-spec-item">
                                    <div class="train-spec-item-label">Color Saturation Mean</div>
                                    <div class="train-spec-item-val">{s_mean}</div>
                                </div>
                            </div>
                        </div>
                        """)

    # ── TAB 2: SPEC-MATCH & ANALYZE ──
    with t_match:
        _render_html("<div style='margin-top: 1.2rem;'></div>")
        left_m, mid_m, right_m = st.columns([1, 2.8, 1])
        with mid_m:
            _render_html("""
            <div class="upload-card-head glass-card" style="margin-bottom: 1.2rem;">
                <div class="glass-title">Test Suspect Photo Against Trained Knowledge Bank</div>
            </div>
            """)

            test_file = st.file_uploader(
                "Upload suspect image to check if its specs match trained photos",
                type=["png", "jpg", "jpeg", "webp"],
                key="matcher_uploader",
                label_visibility="collapsed",
            )

            if test_file:
                test_img = Image.open(test_file).convert("RGB")
                
                # Centered preview
                p_c1, p_c2, p_c3 = st.columns([1, 2, 1])
                with p_c2:
                    st.image(test_img, use_container_width=True, caption=f"{test_file.name} ({test_img.width}x{test_img.height}px)")

                _render_html("<div style='margin-top: 1.4rem;'></div>")
                if st.button("Analyze & Spec-Match Against Memory", type="primary", use_container_width=True):
                    with st.spinner("Extracting specs and querying knowledge bank..."):
                        m_res = match_image_against_registry(test_img, threshold=75.0)

                        if m_res.get("matched"):
                            ex = m_res["exemplar"]
                            sim = m_res["similarity"]
                            m_type = m_res["match_type"]
                            v_label = m_res["trained_verdict_label"]
                            inp_specs = m_res.get("specs", {})
                            tgt_specs = ex.get("forensic_specs", {})

                            _render_html(f"""
                            <div class="memory-match-banner">
                                <div class="memory-match-title">TRAINED MEMORY MATCH CONFIRMED ({sim:.1f}% Similarity)</div>
                                <div class="memory-match-sub">
                                    <b>Match Engine:</b> {m_type} &nbsp;·&nbsp; 
                                    <b>Matched Exemplar:</b> {ex.get('filename')} &nbsp;·&nbsp;
                                    <b>Learned Verdict:</b> {v_label}
                                    {f"<br><b>Exemplar Notes:</b> {ex.get('notes')}" if ex.get('notes') else ""}
                                </div>
                            </div>
                            """)

                            if tgt_specs:
                                inp_res_str = f"{inp_specs.get('resolution',{}).get('width','?')}x{inp_specs.get('resolution',{}).get('height','?')}"
                                tgt_res_str = f"{tgt_specs.get('resolution',{}).get('width','?')}x{tgt_specs.get('resolution',{}).get('height','?')}"
                                _render_html(f"""
                                <table class="spec-diff-table">
                                    <thead>
                                        <tr>
                                            <th>FORENSIC METRIC</th>
                                            <th>TEST IMAGE</th>
                                            <th>MATCHED EXEMPLAR</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>Resolution</td>
                                            <td>{inp_res_str}</td>
                                            <td>{tgt_res_str}</td>
                                        </tr>
                                        <tr>
                                            <td>FFT High-Freq Ratio</td>
                                            <td>{inp_specs.get('frequency_specs',{}).get('high_frequency_ratio',0)}</td>
                                            <td>{tgt_specs.get('frequency_specs',{}).get('high_frequency_ratio',0)}</td>
                                        </tr>
                                        <tr>
                                            <td>Texture Laplacian Variance</td>
                                            <td>{inp_specs.get('texture_specs',{}).get('laplacian_variance',0)}</td>
                                            <td>{tgt_specs.get('texture_specs',{}).get('laplacian_variance',0)}</td>
                                        </tr>
                                        <tr>
                                            <td>Color Saturation Mean</td>
                                            <td>{inp_specs.get('color_profile',{}).get('saturation_mean',0)}</td>
                                            <td>{tgt_specs.get('color_profile',{}).get('saturation_mean',0)}</td>
                                        </tr>
                                        <tr>
                                            <td>Sensor Noise STD</td>
                                            <td>{inp_specs.get('noise_specs',{}).get('sensor_noise_std',0)}</td>
                                            <td>{tgt_specs.get('noise_specs',{}).get('sensor_noise_std',0)}</td>
                                        </tr>
                                    </tbody>
                                </table>
                                """)
                        else:
                            _render_html("<div style='margin-top: 1.2rem;'></div>")
                            st.warning(f"No match found in trained memory bank (Closest Similarity: {m_res.get('similarity', 0.0):.1f}%).")
                            _render_html("<div style='margin-top: 0.8rem;'></div>")
                            if st.button("Run Full 14-Engine Scan Now →", type="secondary", use_container_width=True):
                                st.session_state.scan_image = test_img
                                st.session_state.scan_meta = {
                                    "width": test_img.width,
                                    "height": test_img.height,
                                    "fmt": "JPEG",
                                    "name": test_file.name,
                                }
                                st.session_state.result = full_image_analysis(test_img)
                                st.session_state.page = "results"
                                st.session_state.scan_ready = True
                                st.rerun()

    # ── TAB 3: KNOWLEDGE BANK GALLERY ──
    with t_bank:
        _render_html("<div style='margin-top: 1.2rem;'></div>")
        reg_dict = _get_cached_registry()
        
        _render_html(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.4rem;">
            <h3 style="margin:0;">Learned Memory Bank <code>({len(reg_dict)} Images Remembered)</code></h3>
        </div>
        """)

        if not reg_dict:
            st.info("No images registered yet. Train your first image in Tab 1!")
        else:
            filter_cat = st.selectbox(
                "Filter Knowledge Bank by Ground Truth Category:",
                ["All", "Generated by AI", "AI-Edited", "Authentic / Real"],
            )
            _render_html("<div style='margin-top: 1.2rem;'></div>")

            for sha, item in reg_dict.items():
                lbl = item.get("label", "")
                if filter_cat == "Generated by AI" and lbl not in ("generated_by_ai", "ai"):
                    continue
                if filter_cat == "AI-Edited" and lbl != "ai_edited":
                    continue
                if filter_cat == "Authentic / Real" and lbl != "real":
                    continue

                fn = item.get("filename", "exemplar")
                vrd = item.get("verdict_label", item.get("verdict", ""))
                reg_t = item.get("registered_at", "")
                notes = item.get("notes", "")

                with st.expander(f"{fn} — {vrd}"):
                    c1, c2 = st.columns([1, 1.8], gap="medium")
                    with c1:
                        st.markdown(f"**Ground Truth:** `{lbl}`")
                        st.markdown(f"**Registered:** `{reg_t}`")
                        st.markdown(f"**SHA256:** `{sha[:16]}...`")
                        st.markdown(f"**dHash:** `{item.get('dhash','')[:18]}...`")
                        if notes:
                            st.markdown(f"**Notes:** {notes}")
                    with c2:
                        sp = item.get("forensic_specs", {})
                        if sp:
                            st.markdown(textwrap.dedent(f"""
                            - **Resolution:** `{sp.get('resolution',{}).get('width')}x{sp.get('resolution',{}).get('height')}`
                            - **FFT High-Freq Ratio:** `{sp.get('frequency_specs',{}).get('high_frequency_ratio')}`
                            - **Texture Sharpness:** `{sp.get('texture_specs',{}).get('laplacian_variance')}`
                            - **Saturation Mean:** `{sp.get('color_profile',{}).get('saturation_mean')}`
                            - **Sensor Noise STD:** `{sp.get('noise_specs',{}).get('sensor_noise_std')}`
                            """).strip())


# ──────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────

_render_html(
    '<div class="footer-text">NEXUS+ <span>·</span> AI Detector v7.0 <span>·</span> '
    '14-Engine Multi-Domain Forensics + AI Judge <span>·</span> '
    'HuggingFace + OpenAI CLIP + FFT + Inpainting Forensics</div>'
)
