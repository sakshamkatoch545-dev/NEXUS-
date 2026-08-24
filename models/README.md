# NEXUS+ Pretrained AI-Image Detection Models Subsystem

A local, offline, multi-model AI-generated image detection subsystem integrated into **NEXUS+**. It hosts multiple freely available pretrained models, performs unified probability inference, applies calibrated Bayesian score fusion, and integrates seamlessly with local forensic frequency and texture signals.

---

## 📁 System Structure

```
models/
├── README.md                 # Complete documentation & usage guide
├── MODELS.md                 # Technical specifications, model cards & licenses
├── requirements-models.txt   # Model dependency specifications
├── calibration_config.json   # Configurable decision thresholds & reliability weights
├── download_models.py        # Offline downloader with resume, integrity checks & license reporting
├── registry.py               # Central registry for model specs, metadata, and architectures
├── inference.py              # Unified inference engine with CUDA/CPU auto-detection & lazy loading
├── fusion.py                 # Calibrated ensemble fusion, reliability weighting & forensic integration
├── calibration.py            # Automated threshold calibration tool for validation datasets
├── test_models.py            # Quality control test suite for edge cases (compression, resize, formats)
└── cache/                    # Local storage for all model weight checkpoints
    ├── capcheck/             # CapCheck ViT (Apache-2.0)
    ├── divine2k/             # Divine2k ResNet-50, EfficientNet-B0, ConvNeXt-Tiny (MIT)
    ├── dear/                 # DEAR Corvi ResNet-50 (CC-BY-NC-4.0)
    └── communityforensics/   # Reju983 FrequencyAwareDetector (Apache-2.0)
```

---

## ⚙️ Installation & Setup

Install model dependencies:
```bash
pip install -r models/requirements-models.txt
```

---

## 📥 Downloading Model Weights

### Download All Compatible Models
Downloads all enabled model weights into `models/cache/` with progress tracking and integrity checks:
```bash
python models/download_models.py
```

### Download a Single Targeted Model
```bash
# Download only CapCheck Vision Transformer
python models/download_models.py --model capcheck_vit

# Download only Divine2k ResNet-50
python models/download_models.py --model divine2k_resnet50

# Force re-download even if already cached
python models/download_models.py --force
```

---

## 🚀 Running Local Inference

### Unified CLI Command
Run all downloaded models on any image:
```bash
python models/inference.py --image path/to/image.jpg
```

### Output JSON Format
```bash
python models/inference.py --image path/to/image.jpg --json
```

### Python API Integration
```python
from models.inference import detect_image
from models.fusion import fuse_predictions

# 1. Run all active pretrained models
results = detect_image("sample_images/ai 1.jpeg")

# 2. Fuse predictions into a calibrated verdict
fused = fuse_predictions(results)

print("Final Verdict :", fused["verdict"])          # REAL | LIKELY_AI | AI_GENERATED | UNDETERMINED
print("AI Probability:", fused["ai_probability"])    # 0.0 to 1.0
print("Uncertainty   :", fused["uncertainty"])       # 0.0 to 1.0
```

---

## ⚖️ Score Fusion & Calibration

### Fusion Formula
Given individual model probabilities $P_i$ and reliability weights $w_i$:

$$\bar{P}_{\text{AI}} = \frac{\sum_{i} w_i \cdot P_{\text{AI}, i}}{\sum_{i} w_i}$$

$$\text{Uncertainty} = \min\left(1.0, 4.0 \cdot \frac{\sum_i w_i (P_i - \bar{P}_{\text{AI}})^2}{\sum w_i}\right)$$

### Verdict Mapping
- **`AI_GENERATED`**: $\bar{P}_{\text{AI}} \ge \text{AI\_THRESHOLD}$ (Default: `0.65`)
- **`LIKELY_AI`**: $0.50 \le \bar{P}_{\text{AI}} < \text{AI\_THRESHOLD}$
- **`REAL`**: $\bar{P}_{\text{AI}} \le \text{REAL\_THRESHOLD}$ (Default: `0.35`)
- **`UNDETERMINED`**: High uncertainty / model disagreement or probability in border zone.

### Calibrating Thresholds on Your Dataset
Optimize thresholds on your labeled validation dataset:
```bash
python models/calibration.py --data data/dataset --save
```

---

## 🧪 Quality Control & Testing

Run the automated test suite covering 10 real-world edge cases (JPEG compression, resizing, screenshots, edits, high-res, low-res, WebP, PNG, offline validation):
```bash
python models/test_models.py
```

---

## 📜 Model Licensing & Compliance

| Model Key | Source Repository | License | Commercial Permitted |
| :--- | :--- | :--- | :--- |
| `capcheck_vit` | `capcheck/ai-image-detection` | **Apache-2.0** | **YES** |
| `divine2k_resnet50` | `divine2k/ai-image-detectors` | **MIT** | **YES** |
| `divine2k_efficientnet` | `divine2k/ai-image-detectors` | **MIT** | **YES** |
| `divine2k_convnext` | `divine2k/ai-image-detectors` | **MIT** | **YES** |
| `dear_corvi_resnet50` | `k-aisi-anti-deepfake/dear-checkpoints` | **CC-BY-NC-4.0** | **NO (Research Only)** |
| `reju983_frequency` | `Reju983/ai-generated-image-detector` | **Apache-2.0** | Skipped (Weights missing upstream) |

---

## 💻 Hardware Requirements
- **CPU:** Any modern x86_64 CPU (4+ threads recommended). Average latency: `25ms - 80ms` per model.
- **GPU (Optional):** NVIDIA GPU with CUDA 11.8+ / 12.0+. Average latency: `5ms - 15ms` per model.
- **RAM / VRAM:** $\ge 2\text{ GB}$ system memory / $\ge 1\text{ GB}$ VRAM. Models are lazily loaded to avoid memory bloat.
