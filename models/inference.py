"""
inference.py — Unified Local Inference Engine for Pretrained Detection Models
=============================================================================
Provides a single, standardized, thread-safe inference entry point `detect_image()`
supporting lazy loading, device auto-detection (CUDA/CPU), output normalization,
and per-model error isolation.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from PIL import Image

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure parent and current directory are on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms

from registry import MODEL_REGISTRY, ModelSpec, get_cached_models

try:
    from transformers import ViTForImageClassification, ViTImageProcessor
except ImportError:
    ViTForImageClassification = None
    ViTImageProcessor = None

try:
    import torchvision.models as tv_models
except ImportError:
    tv_models = None


# ─────────────────────────────────────────────────────────────────────────────
# DEVICE SELECTION & RUNTIME STATE
# ─────────────────────────────────────────────────────────────────────────────

def get_default_device() -> torch.device:
    """Auto-detects CUDA GPU if available and functional, else defaults to CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


_LOADED_MODELS: Dict[str, Any] = {}
_LOADED_PROCESSORS: Dict[str, Any] = {}


# ─────────────────────────────────────────────────────────────────────────────
# PREPROCESSING TRANSFORMS
# ─────────────────────────────────────────────────────────────────────────────

def get_standard_transform(image_size: int = 224) -> transforms.Compose:
    """Standard ImageNet evaluation transform."""
    return transforms.Compose([
        transforms.Resize(int(image_size * 1.14), interpolation=transforms.InterpolationMode.BILINEAR),
        transforms.CenterCrop(image_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# MODEL BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_capcheck_vit(spec: ModelSpec, device: torch.device):
    """Loads CapCheck ViT model from local cache directory."""
    if ViTForImageClassification is None:
        raise RuntimeError("transformers library is required for CapCheck ViT")
    local_dir = str(spec.local_dir)
    processor = ViTImageProcessor.from_pretrained(local_dir, local_files_only=True)
    model = ViTForImageClassification.from_pretrained(local_dir, local_files_only=True)
    model.to(device)
    model.eval()
    return model, processor


def _load_divine2k_resnet50(spec: ModelSpec, device: torch.device):
    """Loads Divine2k ResNet-50 binary classifier."""
    if tv_models is None:
        raise RuntimeError("torchvision is required for ResNet-50")
    model = tv_models.resnet50(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 1)
    state_dict = torch.load(str(spec.primary_weight_path), map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model, get_standard_transform(spec.input_size)


def _load_divine2k_efficientnet(spec: ModelSpec, device: torch.device):
    """Loads Divine2k EfficientNet-B0 binary classifier."""
    if tv_models is None:
        raise RuntimeError("torchvision is required for EfficientNet-B0")
    model = tv_models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, 1)
    state_dict = torch.load(str(spec.primary_weight_path), map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model, get_standard_transform(spec.input_size)


def _load_divine2k_convnext(spec: ModelSpec, device: torch.device):
    """Loads Divine2k ConvNeXt-Tiny binary classifier."""
    if tv_models is None:
        raise RuntimeError("torchvision is required for ConvNeXt")
    model = tv_models.convnext_tiny(weights=None)
    in_features = model.classifier[2].in_features
    model.classifier[2] = nn.Linear(in_features, 1)
    state_dict = torch.load(str(spec.primary_weight_path), map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model, get_standard_transform(spec.input_size)


def _load_dear_corvi(spec: ModelSpec, device: torch.device):
    """Loads DEAR Corvi ResNet-50 binary detector."""
    if tv_models is None:
        raise RuntimeError("torchvision is required for DEAR")
    model = tv_models.resnet50(weights=None)
    state_dict = torch.load(str(spec.primary_weight_path), map_location="cpu", weights_only=True)
    # Extract weights if nested inside 'model' or 'state_dict'
    if "model" in state_dict and isinstance(state_dict["model"], dict):
        state_dict = state_dict["model"]
    elif "state_dict" in state_dict and isinstance(state_dict["state_dict"], dict):
        state_dict = state_dict["state_dict"]

    # Adapt classification layer shape if needed
    fc_weight = state_dict.get("fc.weight", None)
    if fc_weight is not None:
        out_features = fc_weight.shape[0]
        model.fc = nn.Linear(model.fc.in_features, out_features)

    # Clean keys if prefixes exist (e.g. module.)
    cleaned_sd = {}
    for k, v in state_dict.items():
        clean_k = k.replace("module.", "").replace("model.", "")
        cleaned_sd[clean_k] = v

    model.load_state_dict(cleaned_sd, strict=False)
    model.to(device)
    model.eval()
    return model, get_standard_transform(spec.input_size)


MODEL_LOADERS = {
    "capcheck_vit": _load_capcheck_vit,
    "divine2k_resnet50": _load_divine2k_resnet50,
    "divine2k_efficientnet": _load_divine2k_efficientnet,
    "divine2k_convnext": _load_divine2k_convnext,
    "dear_corvi_resnet50": _load_dear_corvi,
}


# ─────────────────────────────────────────────────────────────────────────────
# LAZY MODEL INSTANTIATION
# ─────────────────────────────────────────────────────────────────────────────

def get_or_load_model(model_key: str, device: torch.device):
    """Lazy-loads and caches model and preprocessor on the specified device."""
    if model_key in _LOADED_MODELS:
        return _LOADED_MODELS[model_key], _LOADED_PROCESSORS[model_key]

    spec = MODEL_REGISTRY.get(model_key)
    if not spec:
        raise ValueError(f"Unknown model identifier '{model_key}'")

    if not spec.is_cached():
        raise FileNotFoundError(f"Model '{model_key}' weights not found at {spec.primary_weight_path}. Run download_models.py first.")

    loader_fn = MODEL_LOADERS.get(model_key)
    if not loader_fn:
        raise NotImplementedError(f"Loader not implemented for model '{model_key}'")

    model, processor = loader_fn(spec, device)
    _LOADED_MODELS[model_key] = model
    _LOADED_PROCESSORS[model_key] = processor
    return model, processor


# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED INFERENCE DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

def detect_image(
    image: Union[str, Path, Image.Image],
    models: Optional[List[str]] = None,
    device: Optional[Union[str, torch.device]] = None,
) -> Dict[str, Any]:
    """
    Unified inference function for all pretrained AI detection models.

    Args:
        image: File path or PIL Image instance.
        models: Optional list of model keys to run (defaults to all cached & enabled models).
        device: Device to run inference on ('cuda', 'cpu', or auto-detected).

    Returns:
        Standardized dict containing normalized model predictions, probabilities, and timing.
    """
    dev = torch.device(device) if device else get_default_device()

    # Load PIL image safely without mutation
    if isinstance(image, (str, Path)):
        img_pil = Image.open(str(image)).convert("RGB")
    elif isinstance(image, Image.Image):
        img_pil = image.convert("RGB")
    else:
        raise TypeError(f"Expected image path or PIL.Image, got {type(image)}")

    target_models = models or [m.repo_id if False else k for k, m in MODEL_REGISTRY.items() if m.enabled and m.is_cached()]
    if not target_models:
        target_models = [k for k, m in MODEL_REGISTRY.items() if m.enabled]

    results = {}
    errors = {}

    for model_key in target_models:
        spec = MODEL_REGISTRY.get(model_key)
        if not spec:
            errors[model_key] = f"Unknown model key: {model_key}"
            continue

        if not spec.is_cached():
            errors[model_key] = f"Weights not downloaded locally ({spec.filename})"
            continue

        t_start = time.perf_counter()
        try:
            model, processor = get_or_load_model(model_key, dev)
            
            with torch.inference_mode():
                if spec.framework == "transformers":
                    # HuggingFace Vision Transformer
                    inputs = processor(images=img_pil, return_tensors="pt")
                    inputs = {k: v.to(dev) for k, v in inputs.items()}
                    outputs = model(**inputs)
                    logits = outputs.logits[0]
                    probs = torch.softmax(logits, dim=-1).cpu().numpy()
                    
                    # CapCheck ViT labels: 0: REAL, 1: FAKE
                    p_real = float(probs[0])
                    p_ai = float(probs[1])

                elif model_key.startswith("divine2k_"):
                    # PyTorch Torchvision models (single output logit -> Sigmoid)
                    tensor = processor(img_pil).unsqueeze(0).to(dev)
                    logit = model(tensor).squeeze().cpu().item()
                    # Sigmoid output in divine2k represents P(Real)
                    # Output < 0.45 -> AI, > 0.60 -> Real
                    p_real = float(1.0 / (1.0 + np.exp(-logit)))
                    p_ai = float(1.0 - p_real)

                elif model_key == "dear_corvi_resnet50":
                    # DEAR Corvi ResNet-50
                    tensor = processor(img_pil).unsqueeze(0).to(dev)
                    out = model(tensor).squeeze()
                    if out.ndim == 0 or out.numel() == 1:
                        logit = out.cpu().item()
                        p_ai = float(1.0 / (1.0 + np.exp(-logit)))
                        p_real = float(1.0 - p_ai)
                    else:
                        probs = torch.softmax(out, dim=-1).cpu().numpy()
                        p_real = float(probs[0])
                        p_ai = float(probs[1]) if len(probs) > 1 else float(1.0 - p_real)

                else:
                    raise NotImplementedError(f"Inference routine missing for {model_key}")

            t_elapsed = (time.perf_counter() - t_start) * 1000.0

            # Normalize values into strict [0.0, 1.0] bounds
            p_ai = float(np.clip(p_ai, 0.0, 1.0))
            p_real = float(np.clip(p_real, 0.0, 1.0))
            confidence = float(abs(p_ai - p_real))
            prediction = "AI_GENERATED" if p_ai >= 0.50 else "REAL"

            results[model_key] = {
                "name": spec.name,
                "prediction": prediction,
                "ai_probability": round(p_ai, 4),
                "real_probability": round(p_real, 4),
                "confidence": round(confidence, 4),
                "inference_time_ms": round(t_elapsed, 2),
                "license": spec.license,
                "commercial_use": spec.commercial_use,
                "status": "SUCCESS",
            }

        except Exception as exc:
            t_elapsed = (time.perf_counter() - t_start) * 1000.0
            errors[model_key] = str(exc)
            results[model_key] = {
                "name": spec.name,
                "prediction": "ERROR",
                "ai_probability": 0.5,
                "real_probability": 0.5,
                "confidence": 0.0,
                "inference_time_ms": round(t_elapsed, 2),
                "license": spec.license,
                "commercial_use": spec.commercial_use,
                "status": "FAILED",
                "error": str(exc),
            }

    return {
        "device": str(dev),
        "models": results,
        "errors": errors,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run pretrained AI image detection on an image.")
    parser.add_argument("--image", type=str, required=True, help="Path to input image")
    parser.add_argument("--device", type=str, default=None, help="Device to use ('cpu' or 'cuda')")
    parser.add_argument("--json", action="store_true", help="Output results as raw JSON")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"❌ Error: Image path '{args.image}' not found.")
        sys.exit(1)

    print(f"Running inference on: {args.image} (Device: {args.device or get_default_device()}) ...")
    output = detect_image(args.image, device=args.device)

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print("\n" + "=" * 80)
        print(" PRETRAINED MODEL DETECTION RESULTS ")
        print("=" * 80)
        print(f"{'Model Name':<28} | {'Prediction':<14} | {'AI Prob':<9} | {'Real Prob':<9} | {'Latency'}")
        print("-" * 80)
        for k, v in output["models"].items():
            if v["status"] == "SUCCESS":
                print(f"{v['name']:<28} | {v['prediction']:<14} | {v['ai_probability']*100:>6.1f}%  | {v['real_probability']*100:>6.1f}%  | {v['inference_time_ms']:>6.1f} ms")
            else:
                print(f"{v['name']:<28} | {'FAILED':<14} | {'N/A':<9} | {'N/A':<9} | {v.get('error', 'Error')[:25]}")
        print("=" * 80)
