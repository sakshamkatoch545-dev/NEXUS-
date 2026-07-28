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

* {{ font-family: 'JetBrains Mono', monospace !important; box-sizing: border-box; }}

/* ── Reusable entrance animations ── */
@keyframes fadeInUp {{
    0%   {{ opacity: 0; transform: translateY(18px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes popIn {{
    0%   {{ opacity: 0; transform: scale(.92); }}
    70%  {{ opacity: 1; transform: scale(1.015); }}
    100% {{ opacity: 1; transform: scale(1); }}
}}
@keyframes pulseGlowRing {{
    0%, 100% {{ box-shadow: 0 8px 32px rgba(0,0,0,.35), 0 0 0 0 var(--glow); }}
    50%      {{ box-shadow: 0 8px 32px rgba(0,0,0,.35), 0 0 26px 4px var(--glow); }}
}}

/* ── NEXUS v6.0 Background ── */
html, body, [data-testid="stAppViewContainer"] {{
    background-color: var(--bg) !important;
    background-image:
        radial-gradient(circle at 15% 20%, rgba(139,92,246,.16), transparent 45%),
        radial-gradient(circle at 85% 15%, rgba(79,141,255,.14), transparent 45%),
        radial-gradient(circle at 50% 85%, rgba(94,244,255,.10), transparent 50%);
    color: #e2e8f0;
    min-height: 100vh;
}}

/* ── Animated blobs + particles (behind everything) ── */
.nexus-bg {{
    position: fixed;
    inset: 0;
    z-index: -2;
    overflow: hidden;
    pointer-events: none;
}}
.blob {{
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: .55;
    animation: floatBlob 20s ease-in-out infinite;
}}
.blob-1 {{
    width: 420px; height: 420px; top: -100px; left: -80px;
    background: radial-gradient(circle, rgba(139,92,246,.55), transparent 70%);
    animation-duration: 22s;
}}
.blob-2 {{
    width: 380px; height: 380px; top: 40%; right: -120px;
    background: radial-gradient(circle, rgba(79,141,255,.5), transparent 70%);
    animation-duration: 26s; animation-delay: -6s;
}}
.blob-3 {{
    width: 340px; height: 340px; bottom: -120px; left: 30%;
    background: radial-gradient(circle, rgba(94,244,255,.4), transparent 70%);
    animation-duration: 30s; animation-delay: -12s;
}}
@keyframes floatBlob {{
    0%   {{ transform: translate(0,0) scale(1); }}
    33%  {{ transform: translate(40px,-30px) scale(1.08); }}
    66%  {{ transform: translate(-30px,20px) scale(0.95); }}
    100% {{ transform: translate(0,0) scale(1); }}
}}
.particle {{
    position: absolute;
    width: 3px; height: 3px;
    background: var(--accent-cyan);
    border-radius: 50%;
    opacity: .5;
    animation: floatParticle linear infinite;
    box-shadow: 0 0 6px var(--accent-cyan);
}}
@keyframes floatParticle {{
    0%   {{ transform: translateY(0) translateX(0); opacity: 0; }}
    10%  {{ opacity: .6; }}
    90%  {{ opacity: .6; }}
    100% {{ transform: translateY(-100vh) translateX(30px); opacity: 0; }}
}}
.noise-overlay {{
    position: fixed; inset: 0; z-index: -1; pointer-events: none; opacity: .025;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}}

/* ── Rotating aurora sweep — adds continuous background motion ── */
.aurora-sweep {{
    position: absolute;
    inset: -50%;
    background: conic-gradient(
        from 0deg,
        transparent 0deg,
        rgba(139,92,246,.10) 60deg,
        transparent 130deg,
        rgba(94,244,255,.09) 210deg,
        transparent 280deg,
        rgba(79,141,255,.08) 330deg,
        transparent 360deg
    );
    animation: spinAurora 40s linear infinite;
    mix-blend-mode: screen;
}}
@keyframes spinAurora {{
    0%   {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}

/* ── Slow-drifting base gradient (subtle continuous parallax) ── */
[data-testid="stAppViewContainer"] {{
    background-size: 200% 200% !important;
    animation: driftBackground 34s ease-in-out infinite;
}}
@keyframes driftBackground {{
    0%   {{ background-position: 0% 0%; }}
    50%  {{ background-position: 100% 100%; }}
    100% {{ background-position: 0% 0%; }}
}}

[data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
#MainMenu, footer, header {{ visibility: hidden; }}
div[data-testid="stDecoration"] {{ display: none; }}
div[data-testid="stStatusWidget"] {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}

.block-container {{
    padding: 2rem 2.5rem !important;
    max-width: 1400px !important;
    position: relative; z-index: 1;
}}

::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: rgba(255,255,255,.02); }}
::-webkit-scrollbar-thumb {{
    background: linear-gradient(180deg, var(--primary), var(--accent-blue));
    border-radius: 10px;
}}
::-webkit-scrollbar-thumb:hover {{ background: var(--accent-cyan); }}

/* ── Typography ── */
h1 {{
    font-size: 3rem !important;
    font-weight: 800 !important;
    letter-spacing: 2px;
    background: linear-gradient(90deg, var(--accent-cyan) 0%, var(--primary) 50%, var(--accent-blue) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0 !important;
    line-height: 1.2 !important;
    text-align: center !important;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace !important;
}}
.subtitle {{
    font-family: 'JetBrains Mono', monospace !important;
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 3px;
    margin-bottom: 2rem;
    text-transform: uppercase;
    text-align: center;
    display: none;
}}
.version-badge {{
    display: inline-block;
    color: rgba(226,232,240,.9);
    font-size: 1.4rem;
    font-weight: 400;
    font-family: 'JetBrains Mono', monospace !important;
    letter-spacing: 2px;
    margin-left: 0.5rem;
    vertical-align: middle;
    -webkit-text-fill-color: rgba(226,232,240,.9);
}}

/* ── GLASS TABS ── */
[data-testid="stTabs"] [role="tablist"] {{
    background: var(--glass) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 10px !important;
    padding: 0.3rem !important;
    gap: 0.3rem !important;
    margin-bottom: 1.2rem !important;
    backdrop-filter: blur(18px);
}}
[data-testid="stTabs"] button[role="tab"] {{
    background: transparent !important;
    color: var(--muted) !important;
    border: none !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    padding: 0.6rem 1rem !important;
    transition: all 0.2s ease !important;
    font-family: 'JetBrains Mono', monospace !important;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    background: linear-gradient(90deg, var(--primary), var(--accent-blue)) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 18px var(--glow) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none !important; }}

/* ── GLASS CARD ── */
.glass-card {{
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1.5rem 1.6rem;
    margin-bottom: 1.2rem;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.05);
    transition: border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
    animation: fadeInUp 0.55s cubic-bezier(0.16, 1, 0.3, 1) both;
}}
.glass-card::before {{ display: none; }}
.glass-card:hover {{
    border-color: rgba(139,92,246,.35);
    transform: translateY(-3px);
    box-shadow: 0 14px 40px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.06);
}}

.glass-title {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: #ffffff;
    margin-bottom: 1.1rem;
    display: flex;
    align-items: center;
    gap: 0;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace !important;
}}
.glass-title::before {{ display: none; }}

/* ── File Uploader (NEXUS v6.0 drag & drop zone) ── */
[data-testid="stFileUploader"] {{
    background: rgba(139,92,246,.045) !important;
    border: 2px dashed rgba(139,92,246,.45) !important;
    padding: 1.2rem !important;
    border-radius: 16px !important;
    transition: all 0.3s ease;
}}
[data-testid="stFileUploader"]:hover {{
    border-color: var(--accent-cyan) !important;
    background: rgba(94,244,255,.06) !important;
    box-shadow: 0 0 30px rgba(94,244,255,.12);
}}
div[data-testid="stFileUploaderDropzoneInstructions"] > div > span {{
    display: none;
}}
div[data-testid="stFileUploaderDropzoneInstructions"] svg {{ display: none; }}
[data-testid="stFileUploaderDropzone"] button {{ display: none !important; }}
div[data-testid="stFileUploaderDropzoneInstructions"]::before {{
    content: "⬆";
    font-size: 34px;
    display: block;
    text-align: center;
    color: var(--accent-cyan);
    text-shadow: 0 0 18px var(--glow);
    margin-bottom: 6px;
}}
div[data-testid="stFileUploaderDropzoneInstructions"]::after {{
    content: "Drag & Drop Profile Image\\A PNG • JPG • JPEG • WEBP";
    white-space: pre;
    display: block;
    text-align: center;
    font-size: 13px;
    color: var(--muted);
    font-weight: 600;
    letter-spacing: .3px;
    font-family: 'JetBrains Mono', monospace !important;
}}
section[data-testid="stFileUploadDropzone"] {{ min-height: 170px; }}

label[data-testid="stWidgetLabel"] p {{
    color: var(--muted) !important;
    font-size: 0.68rem !important;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 600 !important;
    font-family: 'JetBrains Mono', monospace !important;
}}

/* ── Primary Button (Execute Scan) ── */
.stButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {{
    background: linear-gradient(90deg, var(--primary), var(--secondary), var(--accent-blue)) !important;
    background-size: 200% 100%;
    border: none !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    letter-spacing: 2.5px !important;
    text-transform: uppercase !important;
    padding: 0.85rem !important;
    width: 100%;
    transition: all 0.2s ease !important;
    font-size: 0.82rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    box-shadow: 0 4px 20px var(--glow) !important;
    position: relative;
    overflow: hidden;
    animation: shineGlow 5s ease infinite;
}}
@keyframes shineGlow {{
    0%   {{ background-position: 0% 50%; }}
    50%  {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}
.stButton > button[kind="primary"]::before,
button[data-testid="baseButton-primary"]::before {{
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(circle, rgba(255,255,255,.35) 0%, transparent 65%);
    opacity: 0;
    transform: scale(0.4);
    transition: opacity 0.5s ease, transform 0.5s ease;
    pointer-events: none;
}}
.stButton > button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {{
    box-shadow: 0 6px 28px var(--glow) !important;
    transform: translateY(-2px) scale(1.015) !important;
}}
.stButton > button[kind="primary"]:hover::before,
button[data-testid="baseButton-primary"]:hover::before {{ opacity: .5; transform: scale(1); }}
.stButton > button[kind="primary"]:active,
button[data-testid="baseButton-primary"]:active {{
    transform: translateY(0) scale(0.98) !important;
    transition: transform 0.08s ease !important;
}}
.stButton > button[kind="primary"]:disabled,
button[data-testid="baseButton-primary"]:disabled {{
    opacity: .35 !important;
    animation: none !important;
    box-shadow: none !important;
    cursor: not-allowed !important;
    transform: none !important;
}}

/* ── Secondary / Ghost Button (Cancel, Back, New Scan) ── */
.stButton > button[kind="secondary"],
button[data-testid="baseButton-secondary"] {{
    background: rgba(255,255,255,.03) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 10px !important;
    color: rgba(226,232,240,.85) !important;
    font-weight: 600 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    padding: 0.7rem !important;
    width: 100%;
    font-size: 0.72rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    transition: all 0.2s ease !important;
    backdrop-filter: blur(10px);
}}
.stButton > button[kind="secondary"]:hover,
button[data-testid="baseButton-secondary"]:hover {{
    border-color: var(--danger) !important;
    color: var(--danger) !important;
    background: rgba(255,92,138,.08) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(255,92,138,.15) !important;
}}
.stButton > button[kind="secondary"]:active,
button[data-testid="baseButton-secondary"]:active {{ transform: translateY(0) scale(0.98) !important; }}

/* ── Back-to-home button gets an accent hover instead of danger ── */
.back-btn-wrap .stButton > button[kind="secondary"]:hover,
.back-btn-wrap button[data-testid="baseButton-secondary"]:hover {{
    border-color: var(--accent-cyan) !important;
    color: var(--accent-cyan) !important;
    background: rgba(94,244,255,.08) !important;
    box-shadow: 0 4px 16px rgba(94,244,255,.15) !important;
}}

/* ── Page fade-in wrapper ── */
.page-fade {{ animation: fadeInUp 0.5s cubic-bezier(0.16,1,0.3,1) both; }}

/* ── Results page section heading ── */
.section-heading {{
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin: 2rem 0 1.1rem;
    animation: fadeInUp 0.5s ease both;
}}
.section-heading .sh-icon {{ font-size: 1.3rem; }}
.section-heading .sh-text {{
    font-size: 0.95rem;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #ffffff;
}}
.section-heading .sh-line {{
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(139,92,246,.4), transparent);
}}

/* ── Homepage hero centering ── */
.home-title-wrap {{ text-align: center; margin-bottom: 0.5rem; }}
.home-eyebrow {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--accent-cyan);
    opacity: .8;
    margin-bottom: 0.6rem;
    animation: fadeInUp 0.5s ease both;
}}

/* ── Engine chip strip (homepage teaser) ── */
.engine-chip-strip {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    justify-content: center;
    margin-top: 1rem;
}}
.engine-chip {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--muted);
    background: var(--glass);
    border: 1px solid var(--glass-border);
    padding: 0.32rem 0.7rem;
    border-radius: 50px;
    transition: all 0.2s ease;
    animation: fadeInUp 0.45s ease both;
}}
.engine-chip:hover {{
    color: var(--accent-cyan);
    border-color: rgba(94,244,255,.35);
    transform: translateY(-2px);
}}

/* ── Analyzed image mini-preview on results page ── */
.result-thumb-card .img-preview-trigger {{ max-width: 100%; }}
.result-meta-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 0.7rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
    letter-spacing: 1px;
    text-transform: uppercase;
}}

/* ── Verdict Box ── */
.verdict-box {{
    text-align: center;
    padding: 2.5rem 2rem;
    border-radius: 20px;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    animation: popIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}}
.verdict-box::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: inherit;
    filter: brightness(3);
}}

.v-ai   {{
    background: rgba(255,92,138,.08);
    border: 1px solid rgba(255,92,138,.25);
    box-shadow: 0 8px 32px rgba(255,92,138,.15), inset 0 1px 0 rgba(255,92,138,.15);
}}
.v-unc  {{
    background: rgba(246,195,67,.08);
    border: 1px solid rgba(246,195,67,.25);
    box-shadow: 0 8px 32px rgba(246,195,67,.15), inset 0 1px 0 rgba(246,195,67,.15);
}}
.v-real {{
    background: rgba(46,213,115,.08);
    border: 1px solid rgba(46,213,115,.25);
    box-shadow: 0 8px 32px rgba(46,213,115,.15), inset 0 1px 0 rgba(46,213,115,.15);
}}

.verdict-box h2 {{
    font-size: 2.4rem;
    margin: 0 0 0.5rem;
    text-transform: uppercase;
    letter-spacing: 5px;
    font-weight: 700;
}}
.v-ai h2   {{ color: var(--danger); text-shadow: 0 0 30px rgba(255,92,138,.5); }}
.v-unc h2  {{ color: var(--warning); text-shadow: 0 0 30px rgba(246,195,67,.5); }}
.v-real h2 {{ color: var(--success); text-shadow: 0 0 30px rgba(46,213,115,.5); }}

.v-score {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: rgba(226,232,240,.7);
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
}}
.v-score span {{ font-size: 2.8rem; color: #ffffff; font-weight: 700; display: block; }}

.verdict-bar {{
    background: rgba(255,255,255,.06);
    height: 6px;
    border-radius: 3px;
    margin-top: 1.5rem;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,.08);
}}
.verdict-fill {{
    height: 100%;
    border-radius: 3px;
    transition: width 2s cubic-bezier(0.16, 1, 0.3, 1);
}}
.fill-ai   {{ background: linear-gradient(90deg, var(--danger), var(--warning)); }}
.fill-unc  {{ background: linear-gradient(90deg, var(--warning), var(--accent-cyan)); }}
.fill-real {{ background: linear-gradient(90deg, var(--success), var(--accent-cyan)); }}

/* ── Metric Cards ── */
.metric-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.5rem;
}}
.metric-card {{
    border-radius: 16px;
    padding: 1.5rem;
    text-align: center;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}}
.metric-card:hover {{ transform: translateY(-4px) scale(1.02); }}
.metric-grid .metric-card:nth-child(1) {{ animation-delay: .08s; }}
.metric-grid .metric-card:nth-child(2) {{ animation-delay: .18s; }}
.metric-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
}}
.m-human {{
    background: rgba(46,213,115,.07);
    border: 1px solid rgba(46,213,115,.2);
    box-shadow: 0 4px 20px rgba(46,213,115,.08);
}}
.m-human::before {{ background: linear-gradient(90deg, transparent, rgba(46,213,115,.4), transparent); }}
.m-ai {{
    background: rgba(255,92,138,.07);
    border: 1px solid rgba(255,92,138,.2);
    box-shadow: 0 4px 20px rgba(255,92,138,.08);
}}
.m-ai::before {{ background: linear-gradient(90deg, transparent, rgba(255,92,138,.4), transparent); }}
.m-label {{
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    font-weight: 700;
    margin-bottom: 0.5rem;
    font-family: 'JetBrains Mono', monospace !important;
}}
.m-human .m-label {{ color: rgba(46,213,115,.8); }}
.m-ai .m-label {{ color: rgba(255,92,138,.8); }}
.m-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.4rem;
    font-weight: 700;
    color: #ffffff;
    line-height: 1;
}}

/* ── Engine Cards (Reference Style) ── */
.engine-card {{
    background: rgba(12,14,28,.55);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--glass-border);
    border-radius: 18px;
    padding: 1.6rem 1.8rem 1.4rem 2rem;
    margin-bottom: 1.1rem;
    transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
    animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}}
.engine-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    background: linear-gradient(180deg, var(--primary) 0%, var(--accent-cyan) 100%);
    border-radius: 4px 0 0 4px;
}}
.engine-card::after {{
    content: '';
    position: absolute;
    top: -30px; right: -30px;
    width: 130px; height: 130px;
    border-radius: 50%;
    background: var(--glow);
    filter: blur(35px);
    pointer-events: none;
}}
.engine-card:hover {{
    background: rgba(16,18,36,.7);
    border-color: rgba(139,92,246,.32);
    box-shadow: 0 12px 40px rgba(0,0,0,.45);
    transform: translateY(-2px);
}}

.engine-header {{
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin-bottom: 1.1rem;
}}
.engine-icon {{ font-size: 1.2rem; line-height: 1; }}
.engine-name {{
    font-size: 0.73rem;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    color: rgba(226,232,240,.95);
    font-weight: 700;
    flex: 1;
    font-family: 'JetBrains Mono', monospace !important;
}}
.engine-cog {{
    font-size: 0.85rem;
    color: rgba(152,162,179,.4);
    margin-right: 0.5rem;
}}
.engine-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58rem;
    padding: 0.28rem 0.75rem;
    border-radius: 6px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}
.badge-high {{
    background: var(--danger);
    color: #fff;
    box-shadow: 0 2px 10px rgba(255,92,138,.4);
}}
.badge-mod  {{
    background: var(--warning);
    color: #1a1400;
    box-shadow: 0 2px 10px rgba(246,195,67,.4);
}}
.badge-low  {{
    background: var(--success);
    color: #04220f;
    box-shadow: 0 2px 10px rgba(46,213,115,.4);
}}

.engine-score-block {{
    text-align: center;
    margin: 0 0 1rem;
}}
.engine-score-main {{
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 0;
    line-height: 1;
    margin-bottom: 0.3rem;
}}
.engine-val {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 3rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -2px;
    line-height: 1;
}}
.engine-max {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    color: var(--muted);
    font-weight: 500;
    line-height: 1;
    margin-left: 2px;
}}
.engine-pct-sub {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-weight: 500;
}}

.engine-bar {{
    background: rgba(255,255,255,.05);
    height: 5px;
    border-radius: 3px;
    overflow: hidden;
    margin-bottom: 1rem;
}}
.engine-fill {{
    height: 100%;
    border-radius: 3px;
    transition: width 1.8s cubic-bezier(0.16, 1, 0.3, 1);
}}
.efill-hi  {{ background: linear-gradient(90deg, var(--danger), var(--warning)); }}
.efill-mod {{ background: linear-gradient(90deg, var(--warning), #fbbf67); }}
.efill-lo  {{ background: linear-gradient(90deg, var(--success), var(--accent-cyan)); }}

.engine-explain {{
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.73rem;
    color: rgba(226,232,240,.75);
    font-weight: 400;
    line-height: 1.8;
    padding: 0.85rem 1rem;
    background: rgba(0,0,0,.22);
    border-radius: 10px;
    border: none;
}}
.engine-explain b {{ color: #e2e8f0; font-weight: 700; }}

/* ── Spinner ── */
.stSpinner > div > div {{ border-color: var(--accent-cyan) transparent transparent transparent !important; }}

/* ── Active Engine List ── */
.engine-list-item {{
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.6rem 0.9rem;
    border-radius: 50px;
    margin-bottom: 0.4rem;
    background: var(--glass);
    border: 1px solid transparent;
    transition: all 0.2s ease;
    font-size: 0.75rem;
}}
.engine-list-item:hover {{
    background: rgba(139,92,246,.12);
    border-color: rgba(139,92,246,.25);
    transform: translateX(4px);
    box-shadow: 0 4px 14px rgba(139,92,246,.15);
}}
.engine-num {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 700;
    color: var(--accent-cyan);
    min-width: 20px;
    text-align: left;
}}
.engine-list-name {{
    font-weight: 500;
    color: rgba(226,232,240,.9);
    font-size: 0.75rem;
    flex: 1;
    font-family: 'JetBrains Mono', monospace !important;
}}
.engine-list-sub {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    color: var(--muted);
    font-weight: 400;
}}

/* ── Idle State ── */
.idle-glyph {{
    font-size: 3.5rem;
    opacity: 0.85;
    display: block;
    margin: 0 auto 1.2rem;
    filter: drop-shadow(0 0 22px var(--glow));
    animation: floatIcon 4s ease-in-out infinite;
}}
@keyframes floatIcon {{
    0%, 100% {{ transform: translateY(0px); }}
    50% {{ transform: translateY(-10px); }}
}}

/* ── Scanning pulse animation ── */
.scan-pulse {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: var(--accent-cyan);
    letter-spacing: 2px;
    text-transform: uppercase;
    font-weight: 600;
    animation: text-glow 1.5s ease-in-out infinite;
}}
@keyframes text-glow {{
    0%, 100% {{ opacity: 0.7; }}
    50% {{ opacity: 1; }}
}}

/* ── Footer ── */
.footer-text {{
    font-family: 'JetBrains Mono', monospace !important;
    color: var(--muted);
    opacity: .55;
    font-size: 0.65rem;
    font-weight: 400;
    text-align: center;
    letter-spacing: 3px;
    text-transform: uppercase;
    padding: 2rem 0 1rem;
}}
.footer-text span {{ color: var(--primary); opacity: .8; }}

/* ── Image display ── */
[data-testid="stImage"] img {{
    border-radius: 14px !important;
    border: 1px solid var(--glass-border) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,.4) !important;
}}

/* ── Full Image Preview / Lightbox (click-to-zoom, pure CSS) ── */
.img-preview-wrap {{ position: relative; animation: fadeInUp 0.5s ease both; }}
.img-zoom-toggle {{ display: none; }}

.img-preview-trigger {{
    display: block;
    position: relative;
    cursor: zoom-in;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid var(--glass-border);
    box-shadow: 0 8px 32px rgba(0,0,0,.4);
}}
.preview-thumb {{
    display: block;
    width: 100%;
    height: auto;
    transition: transform 0.5s cubic-bezier(0.16,1,0.3,1), filter 0.5s ease;
}}
.img-preview-trigger:hover .preview-thumb {{
    transform: scale(1.035);
    filter: brightness(1.05) saturate(1.1);
}}

/* subtle animated forensic scan-line sweeping over the thumbnail */
.img-preview-trigger::after {{
    content: '';
    position: absolute;
    left: 0; right: 0; height: 40%;
    top: -40%;
    background: linear-gradient(180deg, transparent, rgba(94,244,255,.22), transparent);
    animation: scanSweep 4.5s ease-in-out infinite;
    pointer-events: none;
}}
@keyframes scanSweep {{
    0%   {{ top: -40%; }}
    50%  {{ top: 100%; }}
    100% {{ top: -40%; }}
}}

.img-preview-hint {{
    position: absolute;
    left: 0; right: 0; bottom: 0;
    padding: 0.55rem 0.8rem;
    background: linear-gradient(0deg, rgba(0,0,0,.75), transparent);
    color: rgba(255,255,255,.92);
    font-size: 0.62rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-weight: 600;
    opacity: 0;
    transform: translateY(6px);
    transition: all 0.25s ease;
}}
.img-preview-trigger:hover .img-preview-hint {{ opacity: 1; transform: translateY(0); }}

.img-zoom-overlay {{
    display: none;
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(4,6,16,.92);
    backdrop-filter: blur(22px);
    -webkit-backdrop-filter: blur(22px);
    align-items: center;
    justify-content: center;
    flex-direction: column;
    gap: 1rem;
    cursor: zoom-out;
    animation: fadeInUp 0.25s ease both;
}}
.img-zoom-toggle:checked ~ .img-zoom-overlay {{ display: flex; }}
.img-zoom-full {{
    max-width: 90vw;
    max-height: 80vh;
    border-radius: 16px;
    border: 1px solid var(--glass-border);
    box-shadow: 0 20px 70px rgba(0,0,0,.6), 0 0 60px var(--glow);
    animation: popIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
}}
.img-zoom-meta {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--accent-cyan);
    background: var(--glass);
    border: 1px solid var(--glass-border);
    padding: 0.5rem 1.1rem;
    border-radius: 50px;
    backdrop-filter: blur(10px);
}}
.img-zoom-close-hint {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--muted);
}}

/* ── Summary card ── */
.summary-text {{
    font-size: 0.9rem;
    color: rgba(226,232,240,.85);
    line-height: 1.9;
    font-weight: 400;
}}
.summary-highlight-ai  {{ color: var(--danger); font-weight: 600; }}
.summary-highlight-unc {{ color: var(--warning); font-weight: 600; }}
.summary-highlight-ok  {{ color: var(--success); font-weight: 600; }}

/* ── Divider ── */
.glass-divider {{
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(94,244,255,.25), transparent);
    margin: 1.5rem 0;
    border: none;
}}

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
