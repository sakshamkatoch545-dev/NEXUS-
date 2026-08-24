"""
fusion.py — Calibrated Ensemble Score Fusion & Forensic Signal Integration
==========================================================================
Combines independent model probabilities using reliability weights,
uncertainty estimation, missing-model resilience, and optional forensic signal fusion.
Outputs calibrated verdicts: REAL, LIKELY_AI, AI_GENERATED, or UNDETERMINED.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from registry import MODEL_REGISTRY

CONFIG_PATH = CURRENT_DIR / "calibration_config.json"


def load_calibration_config() -> dict:
    """Loads calibration thresholds and reliability weights."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "thresholds": {
            "real_threshold": 0.35,
            "ai_threshold": 0.65,
            "uncertainty_threshold": 0.20,
        },
        "reliability_weights": {
            "capcheck_vit": 1.2,
            "divine2k_resnet50": 1.0,
            "divine2k_efficientnet": 1.0,
            "divine2k_convnext": 1.1,
            "dear_corvi_resnet50": 1.3,
        },
        "forensic_fusion": {
            "enabled": True,
            "weight": 0.25,
        }
    }


def fuse_predictions(
    inference_result: Dict[str, Any],
    forensic_features: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fuses individual model predictions into a calibrated ensemble verdict.

    Args:
        inference_result: Output from inference.detect_image().
        forensic_features: Optional dictionary of forensic metrics (FFT, ELA, etc.).
        config: Optional custom calibration configuration.

    Returns:
        Structured dictionary with final verdict, probabilities, uncertainty, and breakdown.
    """
    cfg = config or load_calibration_config()
    thresholds = cfg.get("thresholds", {})
    th_real = thresholds.get("real_threshold", 0.35)
    th_ai = thresholds.get("ai_threshold", 0.65)
    th_unc = thresholds.get("uncertainty_threshold", 0.20)
    rel_weights = cfg.get("reliability_weights", {})

    models_data = inference_result.get("models", {})
    
    valid_predictions = []
    total_weight = 0.0

    for model_key, res in models_data.items():
        if res.get("status") != "SUCCESS":
            continue

        p_ai = res.get("ai_probability")
        if p_ai is None:
            continue

        w = rel_weights.get(model_key, 1.0)
        valid_predictions.append((model_key, p_ai, w))
        total_weight += w

    if not valid_predictions:
        return {
            "verdict": "UNDETERMINED",
            "verdict_label": "❓ UNDETERMINED",
            "ai_probability": 0.50,
            "real_probability": 0.50,
            "confidence_score": 50.0,
            "uncertainty": 1.0,
            "model_count": 0,
            "agreement_ratio": 0.0,
            "forensic_boost": 0.0,
            "breakdown": [],
            "explanation": "No active pretrained models produced valid predictions.",
        }

    # 1. Weighted Mean Probability
    fused_ai_prob = sum(p * w for _, p, w in valid_predictions) / total_weight
    fused_real_prob = 1.0 - fused_ai_prob

    # 2. Ensemble Variance & Uncertainty Estimation
    variance = sum(w * ((p - fused_ai_prob) ** 2) for _, p, w in valid_predictions) / total_weight
    uncertainty = float(min(1.0, variance * 4.0))

    # Model votes
    ai_votes = sum(1 for _, p, _ in valid_predictions if p >= 0.50)
    real_votes = len(valid_predictions) - ai_votes
    agreement_ratio = max(ai_votes, real_votes) / len(valid_predictions)

    # 3. Optional Forensic Signal Fusion
    forensic_boost = 0.0
    forensic_info = []
    if forensic_features and cfg.get("forensic_fusion", {}).get("enabled", True):
        f_weight = cfg.get("forensic_fusion", {}).get("weight", 0.25)
        
        # Calculate heuristic forensic risk
        f_risk_signals = []
        if "fft_ratio" in forensic_features and forensic_features["fft_ratio"] < 0.65:
            f_risk_signals.append(("FFT high-frequency deficit", 0.3))
        if "ela_std" in forensic_features and forensic_features["ela_std"] < 12.0:
            f_risk_signals.append(("Uniform ELA error distribution", 0.25))
        if "fine_texture" in forensic_features and forensic_features["fine_texture"] < 5.0:
            f_risk_signals.append(("Extreme spatial over-smoothing", 0.25))
        
        # NOTE: Missing metadata is explicitly NOT counted as an AI indicator
        if f_risk_signals:
            forensic_score = min(1.0, sum(s[1] for s in f_risk_signals))
            # Blend forensic score with model probability
            fused_ai_prob = (fused_ai_prob * (1.0 - f_weight)) + (forensic_score * f_weight)
            fused_real_prob = 1.0 - fused_ai_prob
            forensic_boost = forensic_score * f_weight
            forensic_info = [s[0] for s in f_risk_signals]

    # 4. Calibrated Verdict Decision Rule
    if uncertainty > th_unc and (0.40 <= fused_ai_prob <= 0.60):
        verdict = "UNDETERMINED"
        verdict_label = "❓ UNDETERMINED (High Model Disagreement)"
    elif fused_ai_prob >= th_ai:
        verdict = "AI_GENERATED"
        verdict_label = "🚨 AI_GENERATED"
    elif fused_ai_prob >= 0.50:
        verdict = "LIKELY_AI"
        verdict_label = "⚠️ LIKELY_AI"
    elif fused_ai_prob <= th_real:
        verdict = "REAL"
        verdict_label = "✅ REAL"
    else:
        verdict = "UNDETERMINED"
        verdict_label = "❓ UNDETERMINED"

    return {
        "verdict": verdict,
        "verdict_label": verdict_label,
        "ai_probability": round(float(fused_ai_prob), 4),
        "real_probability": round(float(fused_real_prob), 4),
        "confidence_score": round(float(fused_ai_prob * 100.0), 1),
        "uncertainty": round(uncertainty, 4),
        "model_count": len(valid_predictions),
        "agreement_ratio": round(agreement_ratio, 2),
        "votes": {"ai": ai_votes, "real": real_votes},
        "forensic_boost": round(forensic_boost, 4),
        "forensic_indicators": forensic_info,
    }
