<div align="center">
  <img src="https://img.shields.io/badge/Version-7.0-blue?style=for-the-badge&logo=appveyor" alt="Version 7.0">
  <img src="https://img.shields.io/badge/Python-3.10%2B-green?style=for-the-badge&logo=python" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Streamlit-UI-red?style=for-the-badge&logo=streamlit" alt="Streamlit">
  <img src="https://img.shields.io/badge/PyTorch-Deep%20Learning-orange?style=for-the-badge&logo=pytorch" alt="PyTorch">
  <img src="https://img.shields.io/badge/OpenAI-CLIP-412991?style=for-the-badge&logo=openai" alt="OpenAI CLIP">
  
  <br><br>
  <h1>🔬 NEXUS+ AI Detector v7.0</h1>
  <p><strong>Advanced 14-Engine Forensic Inspection Platform with Meta-Judge Consensus</strong></p>
  <br>
  <img src="screenshots/nexus_idle.png" alt="NEXUS+ App Screenshot - Idle State" width="90%">
  <br>
  <em>The NEXUS+ Glassmorphism Dark UI — ready for a forensic scan</em>
</div>

---

## 📖 Overview

**NEXUS+** is a state-of-the-art, multi-modal image forensic platform engineered to detect AI-generated synthetic media, deepfakes, and localized AI inpainting with absolute precision. In an era where modern diffusion models (Midjourney v6, SDXL, FLUX, DALL-E 3) and generative erase/inpainting tools create hyper-realistic imagery, traditional single-model detection methods fail catastrophically. 

NEXUS+ solves this by cross-referencing **high-level semantic embeddings**, **fine-tuned Vision Transformers**, **wavelet-based sensor noise disparity**, and an **integrated Bayesian Meta-Judge Engine** to expose invisible fingerprints that generative pipelines leave behind.

### ✨ Key Highlights
- 🧠 **14 Specialized Detection Engines** — deep, multi-domain forensic analysis
- ⚖️ **Forensic Judge Meta-Engine** — multi-domain evidence synthesis & Bayesian arbitration
- 🪄 **AI Inpainting & Object-Removal Forensics** — detects real camera photos with localized AI edits
- ⚡ **Instant Verdicts** — AI-Generated / Real but AI-Edited / Uncertain / Authentic  
- 📊 **Per-Engine Breakdown** — see exactly what each of the 14 engines discovered
- 🎨 **Premium Glassmorphism UI** — modern, dark, and responsive interface
- 🔄 **Self-Improving** — supports local fine-tuning with custom datasets

---

## 🖥️ How It Works — Step by Step

### Step 1 — Launch the App

Open your terminal, activate your virtual environment, and run:
```bash
streamlit run app.py
```
Your browser will open automatically at `http://localhost:8501`.

---

### Step 2 — Upload an Image

On the **left column**, drag & drop any image (JPG, PNG, WEBP) into the **Image Payload** card, or click **Browse File** to open a file picker.

<p align="center">
  <img src="sample_images/ai%20image.jpeg" alt="AI Generated Example" width="42%">
  &nbsp; &nbsp;
  <img src="sample_images/American-actress-Sydney-Sweeney-2022.webp" alt="Real Photograph Example" width="42%">
</p>
<p align="center">
  <em>Left: An AI-generated image — Right: A real photograph with natural optical depth and organic sensor grain</em>
</p>

---

### Step 3 — Execute Forensic Scan

Click the glowing **⚡ Execute Forensic Scan** button. The system initiates all 14 engines:
- Neural classification via HuggingFace pipelines
- OpenAI CLIP zero-shot semantic matching
- Computer vision signal analysis (FFT, ELA, multi-scale texture, facial symmetry)
- Donoho Wavelet PRNU sensor noise disparity scan (for localized inpainting)
- Local dataset-trained Vision Transformer inference
- Generator family provenance attribution
- Forensic Meta-Judge Bayesian arbitration

---

### Step 4 — Review the Verdict

The **right column** transforms to show your full forensic report:

<p align="center">
  <img src="screenshots/nexus_results.png" alt="NEXUS+ App Screenshot - Scan Results" width="90%">
</p>

The **verdict panel** displays one of four calibrated outcomes:
| Verdict | Meaning | Badge |
|---|---|---|
| 🚨 **AI-GENERATED** | High-confidence synthetic generation detected across neural and forensic engines | 🔴 Red |
| 🪄 **LIKELY REAL BUT EDITED BY AI** | Genuine camera foundation with localized generative fill, inpainting, or filters | 🟠 Amber |
| ⚠️ **UNCERTAIN** | Borderline or mixed signals requiring human review | 🟡 Yellow |
| ✅ **AUTHENTIC** | Verified natural optical camera capture with uniform sensor noise | 🟢 Green |

---

## 🚀 The 14 Detection Engines

### 🧠 Layer 1 — Neural & Semantic Analysis
| # | Engine | Technology | What it Detects |
|---|---|---|---|
| 01 | **Neural Network Ensemble** | ViT / ResNet Classifier | Multi-layer latent diffusion fingerprints |
| 02 | **CLIP Semantic Analysis** | OpenAI CLIP Zero-Shot | Semantic alignment with AI vs real prompt priors |
| 10 | **Fine-Tuned ViT Classifier** | Custom Local ViT | Hyperrealistic synthetic facial diffusion patterns |

### 🔍 Layer 2 — Signal Processing & Forensic Physics
| # | Engine | Technology | What it Detects |
|---|---|---|---|
| 03 | **Texture Smoothness** | Multi-Scale Micro-Variance | Unnatural synthetic skin and fabric smoothing |
| 05 | **Frequency Domain (FFT)** | 2D Fourier Energy Spectrum | High-frequency sensor noise loss & grid artifacts |
| 09 | **Error Level Analysis (ELA)** | JPEG Quantization Residual | Re-compression error inconsistencies |
| 11 | **Watermark Detection** | Contour & Alignment Analysis | Generator margin logos, text, and signatures |

### 🎨 Layer 3 — Inpainting, Biometrics & Provenance
| # | Engine | Technology | What it Detects |
|---|---|---|---|
| 04 | **Color & Saturation** | HSV Saturation Distribution | Hyper-saturated neon diffusion color palettes |
| 06 | **Background & Edge** | Studio Edge & Depth Check | Synthetic bokeh and cutout edge anomalies |
| 07 | **Portrait Style** | Composition & Framing | Stock-AI framing and portrait templates |
| 08 | **Face Symmetry & Micro-Texture** | Landmark & Pore Geometry | Unnatural bilateral symmetry & waxy skin |
| 12 | **AI Provenance Engine** | Generator-Family Signatures | Midjourney, DALL-E, SDXL, Flux attribution |
| 13 | **AI Inpainting & Retouch Forensics** | Wavelet Residual Disparity | Localized AI generative fill, eraser, & inpainting |

### ⚖️ Layer 4 — Meta-Consensus
| # | Engine | Technology | What it Detects |
|---|---|---|---|
| 14 | **Forensic Judge Engine** | Multi-Domain Bayesian Arbitration | Synthesizes all 13 vectors to produce the final calibrated verdict |

---

## 📁 Project Structure

```text
NEXUS+/
├── app.py                  # Main Streamlit UI application (glassmorphism theme)
├── src/
│   └── detector.py         # Core forensic logic — all 11 detection engines + scoring
├── screenshots/            # App UI screenshots (auto-generated)
├── sample_images/          # Real and AI-generated test images
├── scripts/                # Auxiliary debugging and model training scripts
│   ├── debug_gemini.py
│   ├── diag.py
│   ├── prepare_dataset.py
│   ├── test_detector.py
│   └── test_scoring.py
├── logs/                   # System and training execution logs
├── requirements.txt        # Python dependencies
└── README.md               # This documentation
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.10 or higher
- CUDA-capable GPU (recommended for ViT models; CPU fallback available)

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/sakshamkatoch545-dev/NEXUS-.git
cd NEXUS-

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Install all dependencies
pip install -r requirements.txt

# 4. Run the application
streamlit run app.py
```

---

## 🛡️ License & Disclaimer

<div align="center">
  <p><i>Developed for advanced forensic research, academic study, and synthetic media detection.<br>
  NEXUS+ is an analytical aid tool — no automated detection system is infallible.<br>
  Always apply human expert discretion for critical decisions.</i></p>
  <br>
  <strong>NEXUS+ AI Detector v6.0 &nbsp;·&nbsp; Built with Streamlit, PyTorch, OpenAI CLIP & OpenCV</strong>
</div>
# AI provenance engine (v6)

The detector now includes `ai_provenance`, a dedicated weak-signal engine for
ChatGPT/GPT Image, Gemini/Imagen, and other modern generators. It combines
generator-family semantic compatibility with available EXIF/C2PA hints and
reports `nearest_generator`, `similarity`, `detected_artifacts`, and
`feature_scores` in the main JSON response. It does not claim exact provider
attribution: resizing, screenshots, and social-media recompression can remove
provenance and alter visual evidence.

To enable the multimodal API engine, configure secrets outside source control:

```powershell
$env:GEMINI_API_KEY = "your-gemini-key"
$env:GROQ_API_KEY = "your-groq-key"
streamlit run app.py
```

The code tries Gemini first and Groq vision as a fallback. API keys are never
written to the repository or returned in analysis results.
