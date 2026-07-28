<div align="center">
  <img src="https://img.shields.io/badge/Version-6.0-blue?style=for-the-badge&logo=appveyor" alt="Version 6.0">
  <img src="https://img.shields.io/badge/Python-3.10%2B-green?style=for-the-badge&logo=python" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Streamlit-UI-red?style=for-the-badge&logo=streamlit" alt="Streamlit">
  <img src="https://img.shields.io/badge/PyTorch-Deep%20Learning-orange?style=for-the-badge&logo=pytorch" alt="PyTorch">
  
  <br><br>
  <h1>🔬 NEXUS+ AI Detector v6.0</h1>
  <p><strong>Advanced 11-Engine Forensic Inspection for Synthetic Media Detection</strong></p>
</div>

---

## 📖 Overview

**NEXUS+** is a state-of-the-art, multi-modal image forensic platform engineered to detect AI-generated synthetic media with absolute precision. In an era where diffusion models (like Midjourney v6, SDXL, and DALL-E 3) create hyper-realistic imagery, traditional detection methods fall short. NEXUS+ solves this by leveraging a massive ensemble of **11 specialized detection engines**.

Instead of relying on a single neural network, NEXUS+ cross-references high-level semantic embeddings with microscopic, low-level signal processing (like Fourier transforms, Error Level Analysis, and micro-texture variance) to expose the invisible fingerprints left by AI generators.

---

## 🖼️ Visual Demonstrations

Here is a look at the types of images NEXUS+ processes and evaluates. By understanding the visual artifacts, the engines score the image accordingly.

<p align="center">
  <img src="sample_images/ai%20image.jpeg" alt="AI Generated Example" width="45%">
  &nbsp; &nbsp;
  <img src="sample_images/real%20image.png" alt="Real Photograph Example" width="45%">
</p>
<p align="center">
  <em>Left: A typical AI-generated image with hyper-smooth textures and synthetic lighting. Right: A genuine, real photograph containing natural sensor noise and organic asymmetry.</em>
</p>

---

## 🚀 The 11-Engine Architecture

NEXUS+ doesn't just guess; it calculates the probability of AI generation across 11 distinct forensic domains. 

### 🧠 Neural & Semantic Analysis
1. **Neural Network Ensemble**: Aggregates predictions from multiple HuggingFace image classifiers fine-tuned specifically for AI and deepfake detection. It serves as a baseline high-level semantic check.
2. **CLIP Semantic Analysis**: Utilizes OpenAI's Zero-Shot ViT-B-32 model. We project the image into a latent space and measure its alignment with "synthetic/AI" text embeddings versus "authentic/camera" embeddings.
3. **Fine-Tuned ViT Classifier**: Uses our own custom-trained Vision Transformer (ViT) checkpoint, trained locally on a curated dataset of the latest diffusion outputs for highly robust classification.

### 🔍 Signal Processing & Artifact Detection
4. **Texture Smoothness (Micro-Variance)**: AI models notoriously struggle with true randomness. This engine analyzes multi-scale micro-variance to detect the unnatural pixel-level smoothing common in AI synthesis.
5. **Frequency Domain (FFT)**: Performs a Fast Fourier Transform to analyze the energy spectrum. Real cameras introduce high-frequency sensor noise; AI images typically show a severe deficit in these high-frequency bands.
6. **Error Level Analysis (ELA)**: Re-compresses the image to evaluate JPEG compression residuals. AI synthetic images often present a highly uniform error distribution, whereas authentic photos show variable, organic error levels.
7. **Watermark & Logo Detection**: Automatically scans the image margins for hidden or visible logo/text artifacts commonly injected by commercial generators (like the DALL-E color blocks or Midjourney watermarks).

### 🎨 Composition & Color Forensics
8. **Color & Saturation Forensics**: Measures saturation distributions. AI models tend to produce vivid, hyper-stylized palettes. This engine detects unnatural foreground saturation peaking.
9. **Background & Edge Analysis**: Inspects background uniformity. AI studio portraits often feature flat gradients, artificially perfect edge transitions, and featureless backdrops.
10. **Portrait Style & Framing**: Analyzes composition rules. Detects the common "studio white backdrop" patterns and structural framing uniquely favored by diffusion training datasets.
11. **Face Symmetry & Smoothness**: Leverages facial landmarks to detect unnatural bilateral symmetry (perfectly mirrored features) and over-smoothed skin regions lacking natural pores.

---

## 📁 Project Structure

Our repository is meticulously organized to ensure clean development and easy usage:

```text
NEXUS+/
├── app.py                  # Main Streamlit Glassmorphism UI application
├── src/                    
│   └── detector.py         # Core logic housing all 11 detection engines and PyTorch inference
├── sample_images/          # Sample real and AI-generated images for testing (e.g., ai image.jpeg)
├── scripts/                # Auxiliary scripts for debugging, scoring, and local model training
├── logs/                   # System, Streamlit, and training execution logs
├── requirements.txt        # Python dependencies (Streamlit, Torch, OpenCV, etc.)
└── README.md               # This documentation file
```

---

## ⚙️ Installation & Setup

Get NEXUS+ running on your local machine in just a few minutes.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sakshamkatoch545-dev/NEXUS-.git
   cd NEXUS-
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 💻 Usage Guide

NEXUS+ features a stunning, modern **Glassmorphism Dark UI**. To launch it:

```bash
streamlit run app.py
```

### How to Scan an Image:
1. Open the provided localhost URL in your web browser.
2. **Drag & Drop** an image (JPG, PNG, WEBP) into the upload payload zone.
3. Click the **⚡ Execute Forensic Scan** button.
4. The system will activate the 11 engines. Wait for the computation to finish.
5. **Review the Results**:
   - The **Human vs AI Breakdown** tab gives you the overall threat score and a plain-english summary.
   - The **11-Engine Forensics** tab provides a deep-dive, granular look at exactly what each engine scored and why.

---

## 🛡️ License & Disclaimer
<div align="center">
  <p><i>Developed for advanced forensic research, academic study, and synthetic media detection. <br> NEXUS+ is designed to assist analysts, but no automated tool is 100% infallible. Always use human discretion.</i></p>
</div>
