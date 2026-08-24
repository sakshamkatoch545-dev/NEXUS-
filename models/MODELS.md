# Pretrained AI-Image Detection Models Specification & Registry

This document records the architectural specifications, framework requirements, preprocessing standards, output labels, weight availability, and licensing terms for all target pretrained AI-generated image detection models evaluated for local deployment.

---

## Model Evaluation Matrix

| Model Identifier | Source Repository | Framework | Architecture | Input Res | Labels | Weight Status | License | Commercial Use |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`capcheck_vit`** | `capcheck/ai-image-detection` | Hugging Face Transformers / PyTorch | Vision Transformer (`ViTForImageClassification`) | `224×224` | `0: REAL`, `1: FAKE` | **Available** (`model.safetensors`) | `Apache-2.0` | **Permitted** (Permissive) |
| **`divine2k_resnet50`** | `divine2k/ai-image-detectors` | PyTorch (`torchvision.models.resnet50`) | ResNet-50 Binary Head | `224×224` | `Sigmoid logit (<0.45 AI, >0.60 Real)` | **Available** (`resnet50_ai_real_final.pth`) | `MIT` | **Permitted** (Permissive) |
| **`divine2k_efficientnet`** | `divine2k/ai-image-detectors` | PyTorch (`torchvision.models.efficientnet_b0`) | EfficientNet-B0 Binary Head | `224×224` | `Sigmoid logit (<0.45 AI, >0.60 Real)` | **Available** (`efficientNet_BO_Final.pth`) | `MIT` | **Permitted** (Permissive) |
| **`divine2k_convnext`** | `divine2k/ai-image-detectors` | PyTorch (`torchvision.models.convnext_tiny`) | ConvNeXt-Tiny Binary Head | `224×224` | `Sigmoid logit (<0.45 AI, >0.60 Real)` | **Available** (`convNext_final.pth`) | `MIT` | **Permitted** (Permissive) |
| **`dear_corvi_resnet50`** | `k-aisi-anti-deepfake/dear-checkpoints` | PyTorch (`torchvision.models.resnet50`) | DEAR-Corvi ResNet-50 | `224×224` | `0: Real, 1: AI` | **Available** (`corvi/model_best.pth`) | `CC-BY-NC-4.0` | **Restricted** (Non-Commercial / Research Only) |
| **`reju983_frequency`** | `Reju983/ai-generated-image-detector` | PyTorch / SwinV2 | `FrequencyAwareDetector` (SwinV2 + SRM + DCT + FFT) | `256×256` | `0: Real, 1: AI` | **Unavailable Upstream** (Weights missing in HF repo) | `Apache-2.0` | **Skipped** (Weights not published upstream) |

---

## Detailed Model Reports

### 1. CapCheck ViT (`capcheck_vit`)
- **Hugging Face Hub:** [`capcheck/ai-image-detection`](https://huggingface.co/capcheck/ai-image-detection)
- **Base Architecture:** Google ViT Base (`google/vit-base-patch16-224`) fine-tuned on CIFAKE & diffusion datasets.
- **Framework Requirements:** `transformers>=4.30.0`, `torch>=2.0.0`, `safetensors`.
- **Image Preprocessing:** Resize to `(224, 224)`, RGB normalization `mean=[0.5, 0.5, 0.5]`, `std=[0.5, 0.5, 0.5]`.
- **Output Representation:** Softmax over 2 logits (`0: REAL`, `1: FAKE`).
- **License:** `Apache-2.0` (Permits free commercial and non-commercial redistribution and local execution).
- **Deployment Status:** **Active / Fully Integrated**.

---

### 2. Divine2k Ensemble Suite (`divine2k_resnet50`, `divine2k_efficientnet`, `divine2k_convnext`)
- **Hugging Face Hub:** [`divine2k/ai-image-detectors`](https://huggingface.co/divine2k/ai-image-detectors)
- **Architectures:**
  - `resnet50`: Standard Torchvision ResNet-50 with `fc = nn.Linear(2048, 1)`.
  - `efficientnet_b0`: Torchvision EfficientNet-B0 with modified classifier head.
  - `convnext_tiny`: Torchvision ConvNeXt-Tiny with `classifier[2] = nn.Linear(768, 1)`.
- **Framework Requirements:** `torch>=2.0.0`, `torchvision>=0.15.0`.
- **Training Data:** ~30,000 high-resolution images across SD 1.5, SDXL, Midjourney, DALL-E, and Grok.
- **Image Preprocessing:** Standard ImageNet transform (Resize `256`, CenterCrop `224`, `ToTensor`, `Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])`).
- **Output Representation:** Single logit converted via $\sigma(x)$ into $P(\text{Real})$. $P(\text{AI}) = 1.0 - \sigma(x)$.
- **License:** `MIT License` (Permissive commercial and non-commercial usage with attribution).
- **Deployment Status:** **Active / Fully Integrated**.

---

### 3. DEAR Checkpoints (`dear_corvi_resnet50`)
- **Hugging Face Hub:** [`k-aisi-anti-deepfake/dear-checkpoints`](https://huggingface.co/k-aisi-anti-deepfake/dear-checkpoints)
- **Paper & Reference:** *"Dissect and Prune: Enhancing Robustness in AI-Generated Image Detection"* (ICML 2026).
- **Base Architecture:** Corvi ResNet-50 with Regional Activation Discrepancy channel pruning.
- **Framework Requirements:** `torch>=2.0.0`, `torchvision>=0.15.0`.
- **Image Preprocessing:** Resize `(224, 224)`, ImageNet normalization.
- **Output Representation:** 2-class logits / binary classification.
- **License:** `Creative Commons Attribution-NonCommercial 4.0 International (CC-BY-NC-4.0)`.
- **Commercial Use:** **Strictly Non-Commercial / Research & Evaluation Only**.
- **Deployment Status:** **Active with Non-Commercial flag in Registry**.

---

### 4. Reju983 Frequency-Aware Detector (`reju983_frequency`)
- **Hugging Face Hub:** [`Reju983/ai-generated-image-detector`](https://huggingface.co/Reju983/ai-generated-image-detector)
- **Intended Architecture:** `FrequencyAwareDetector` combining `microsoft/swinv2-tiny-patch4-window8-256`, Spatial Rich Model (SRM 30-filter bank), 2D Discrete Cosine Transform (DCT 8 bands), and FFT power spectrum features.
- **License:** `Apache-2.0`.
- **Upstream Inspection Finding:**
  The repository author published the training code (`train.py`, `kaggle_train.ipynb`), inference script (`inference.py`), and configuration (`detector_config.json`), but **did not upload the trained checkpoint weights file** (`model_state_dict.pt`).
- **Action Taken:** Marked as **Weights Unavailable Upstream**. The download script and model registry gracefully report this status and skip initialization without breaking the ensemble.

---

## Offline Independence & Security
- All enabled models load strictly from local storage in `models/cache/`.
- No remote telemetry, analytics, or external API endpoints are invoked during `inference.py` execution.
- Device detection automatically utilizes NVIDIA CUDA when available and seamlessly falls back to CPU.
