<div align="center">
  <img src="https://img.shields.io/badge/Version-6.0-blue?style=for-the-badge&logo=appveyor" alt="Version 6.0">
  <img src="https://img.shields.io/badge/Python-3.10%2B-green?style=for-the-badge&logo=python" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Streamlit-UI-red?style=for-the-badge&logo=streamlit" alt="Streamlit">
  
  <br><br>
  <h1>NEXUS+ AI Detector v6.0</h1>
  <p><strong>Deep 11-Engine Forensic Inspection for AI Images</strong></p>
</div>

---

## 🔬 Overview
**NEXUS+** is an advanced, multi-modal image forensic tool designed to detect AI-generated synthetic media with high confidence. It leverages an ensemble of **11 specialized detection engines**—combining state-of-the-art neural classifiers (like HuggingFace and OpenAI CLIP) with low-level signal processing and computer vision techniques.

By targeting the unique artifacts left behind by modern diffusion models (SDXL, Midjourney, Stable Diffusion, DALL-E) and GANs, NEXUS+ offers unparalleled accuracy in identifying synthetic imagery.

## 🚀 The 11 Detection Engines
NEXUS+ evaluates images across 11 distinct forensic domains:

1. **Neural Network Ensemble**: Aggregates predictions from HuggingFace image classifiers fine-tuned for AI detection.
2. **CLIP Semantic Analysis**: Uses OpenAI's Zero-Shot ViT-B-32 model to measure alignment with "synthetic" vs "authentic" semantic embeddings.
3. **Texture Smoothness**: Analyzes multi-scale micro-variance to detect the unnatural smoothing common in AI synthesis.
4. **Color & Saturation**: Measures saturation distributions to identify the vivid, hyper-stylized palettes typical of AI models.
5. **Frequency Domain (FFT)**: Performs Fourier Energy Spectrum analysis to identify high-frequency sensor noise deficits.
6. **Background & Edge**: Inspects studio uniformity, flat gradients, and edge sharpness in the image background.
7. **Portrait Style**: Analyzes composition, framing, and common "studio white backdrop" patterns.
8. **Face Symmetry & Smoothness**: Uses facial landmarks to detect unnatural bilateral symmetry and over-smoothed skin regions.
9. **Error Level Analysis (ELA)**: Evaluates JPEG compression residuals to identify inconsistent artifacting.
10. **Fine-Tuned ViT Classifier**: Uses a local, custom-trained Vision Transformer for robust classification.
11. **Watermark Detection**: Scans margins for hidden or visible logo/text artifacts commonly injected by commercial generators.

## 📁 Repository Structure
```text
NEXUS+/
├── app.py                  # Main Streamlit UI application
├── src/                    # Source code directory
│   └── detector.py         # Core logic containing all 11 detection engines
├── sample_images/          # Sample real and AI-generated images for testing
├── scripts/                # Auxiliary scripts for debugging and model training
├── logs/                   # System and training logs
├── requirements.txt        # Python dependencies
└── README.md               # This documentation file
```

## ⚙️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sakshamkatoch545-dev/NEXUS-.git
   cd NEXUS-
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## 💻 Usage

Run the web interface using Streamlit:
```bash
streamlit run app.py
```
This will launch the NEXUS+ Glassmorphism Dark UI in your default web browser.

1. **Upload** an image (JPG, PNG, WEBP).
2. Click **Execute Forensic Scan**.
3. View the **Human vs AI Breakdown** and explore the detailed **11-Engine Forensics** tab to understand exactly *why* an image was flagged.

---
<div align="center">
  <p><i>Developed for advanced forensic research and synthetic media detection.</i></p>
</div>
