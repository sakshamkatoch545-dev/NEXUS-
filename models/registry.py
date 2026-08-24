"""
registry.py — NEXUS+ Pretrained AI-Detection Model Registry
===========================================================
Defines metadata, architecture specifications, label mappings, licenses,
and local cache paths for all integrated detection models.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

ROOT_DIR = Path(__file__).resolve().parent
CACHE_DIR = ROOT_DIR / "cache"


@dataclass
class ModelSpec:
    name: str
    repo_id: str
    filename: str
    subfolder: str
    architecture: str
    framework: str
    input_size: int
    license: str
    commercial_use: bool
    enabled: bool
    reliability_weight: float
    raw_labels: Dict[str, int] = field(default_factory=dict)
    notes: str = ""
    extra_files: List[str] = field(default_factory=list)

    @property
    def local_dir(self) -> Path:
        return CACHE_DIR / self.subfolder

    @property
    def primary_weight_path(self) -> Path:
        return self.local_dir / self.filename

    def is_cached(self) -> bool:
        path = self.primary_weight_path
        return path.exists() and path.stat().st_size > 0


MODEL_REGISTRY: Dict[str, ModelSpec] = {
    "capcheck_vit": ModelSpec(
        name="CapCheck ViT Detector",
        repo_id="capcheck/ai-image-detection",
        filename="model.safetensors",
        subfolder="capcheck",
        architecture="ViTForImageClassification",
        framework="transformers",
        input_size=224,
        license="Apache-2.0",
        commercial_use=True,
        enabled=True,
        reliability_weight=1.2,
        raw_labels={"REAL": 0, "FAKE": 1},
        notes="Fine-tuned Vision Transformer (ViT-Base-224) on CIFAKE diffusion datasets.",
        extra_files=["config.json", "preprocessor_config.json"],
    ),
    "divine2k_resnet50": ModelSpec(
        name="Divine2k ResNet-50",
        repo_id="divine2k/ai-image-detectors",
        filename="resnet50_ai_real_final.pth",
        subfolder="divine2k",
        architecture="torchvision_resnet50",
        framework="torch",
        input_size=224,
        license="MIT",
        commercial_use=True,
        enabled=True,
        reliability_weight=1.0,
        raw_labels={"AI": 0, "REAL": 1},
        notes="Trained on ~30k multi-generator synthetic images (SDXL, Midjourney, DALL-E, Grok).",
    ),
    "divine2k_efficientnet": ModelSpec(
        name="Divine2k EfficientNet-B0",
        repo_id="divine2k/ai-image-detectors",
        filename="efficientNet_BO_Final.pth",
        subfolder="divine2k",
        architecture="torchvision_efficientnet_b0",
        framework="torch",
        input_size=224,
        license="MIT",
        commercial_use=True,
        enabled=True,
        reliability_weight=1.0,
        raw_labels={"AI": 0, "REAL": 1},
        notes="EfficientNet-B0 backbone fine-tuned for generative artifact identification.",
    ),
    "divine2k_convnext": ModelSpec(
        name="Divine2k ConvNeXt-Tiny",
        repo_id="divine2k/ai-image-detectors",
        filename="convNext_final.pth",
        subfolder="divine2k",
        architecture="torchvision_convnext_tiny",
        framework="torch",
        input_size=224,
        license="MIT",
        commercial_use=True,
        enabled=True,
        reliability_weight=1.1,
        raw_labels={"AI": 0, "REAL": 1},
        notes="Modern ConvNeXt-Tiny convolutional vision backbone.",
    ),
    "dear_corvi_resnet50": ModelSpec(
        name="DEAR Corvi ResNet-50",
        repo_id="k-aisi-anti-deepfake/dear-checkpoints",
        filename="corvi/model_best.pth",
        subfolder="dear",
        architecture="dear_corvi_resnet50",
        framework="torch",
        input_size=224,
        license="CC-BY-NC-4.0",
        commercial_use=False,
        enabled=True,
        reliability_weight=1.3,
        raw_labels={"REAL": 0, "AI": 1},
        notes="ICML 2026 DEAR framework checkpoint with Regional Activation Discrepancy channel filtering.",
    ),
    "reju983_frequency": ModelSpec(
        name="Reju983 Frequency-Aware SwinV2",
        repo_id="Reju983/ai-generated-image-detector",
        filename="model_state_dict.pt",
        subfolder="communityforensics",
        architecture="FrequencyAwareDetector",
        framework="torch",
        input_size=256,
        license="Apache-2.0",
        commercial_use=True,
        enabled=False,  # Weights missing upstream on Hugging Face
        reliability_weight=1.0,
        raw_labels={"real": 0, "ai_generated": 1},
        notes="Weights (.pt) omitted upstream on Hugging Face. Config and code only.",
    ),
}


def get_model_spec(model_id: str) -> Optional[ModelSpec]:
    return MODEL_REGISTRY.get(model_id)


def list_models() -> List[ModelSpec]:
    return list(MODEL_REGISTRY.values())


def get_enabled_models() -> List[ModelSpec]:
    return [m for m in MODEL_REGISTRY.values() if m.enabled]


def get_cached_models() -> List[ModelSpec]:
    return [m for m in MODEL_REGISTRY.values() if m.enabled and m.is_cached()]
