"""
calibration.py — Threshold Calibration & Metric Optimization Tool
=================================================================
Evaluates ensemble predictions on a validation dataset and tunes
REAL_THRESHOLD, AI_THRESHOLD, and model reliability weights to optimize
F1-score, precision, and false-positive rates.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from inference import detect_image
from fusion import fuse_predictions, load_calibration_config, CONFIG_PATH


def evaluate_thresholds(
    y_true: List[int],  # 0: Real, 1: AI
    y_prob: List[float],
    real_th: float,
    ai_th: float
) -> Dict[str, float]:
    """Calculates accuracy, precision, recall, F1, and undetermined rate."""
    tp, fp, tn, fn, und = 0, 0, 0, 0, 0
    for true, prob in zip(y_true, y_prob):
        if prob >= ai_th:
            pred = 1
        elif prob <= real_th:
            pred = 0
        else:
            und += 1
            continue

        if pred == 1 and true == 1:
            tp += 1
        elif pred == 1 and true == 0:
            fp += 1
        elif pred == 0 and true == 0:
            tn += 1
        elif pred == 0 and true == 1:
            fn += 1

    decided = len(y_true) - und
    acc = (tp + tn) / decided if decided > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    und_rate = und / len(y_true) if len(y_true) > 0 else 0.0

    return {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "undetermined_rate": und_rate,
        "decided_samples": decided,
        "total_samples": len(y_true),
    }


def calibrate_on_dataset(val_dir: str, save: bool = False) -> Dict[str, any]:
    """
    Runs inference across val_dir/real and val_dir/ai subdirectories,
    scans threshold combinations, and finds the optimal F1-score configuration.
    """
    val_path = Path(val_dir)
    real_dir = val_path / "real"
    ai_dir = val_path / "ai"

    if not real_dir.exists() or not ai_dir.exists():
        raise FileNotFoundError(f"Validation directory must contain 'real' and 'ai' subfolders: {val_dir}")

    real_images = list(real_dir.glob("*.jpg")) + list(real_dir.glob("*.png")) + list(real_dir.glob("*.jpeg"))
    ai_images = list(ai_dir.glob("*.jpg")) + list(ai_dir.glob("*.png")) + list(ai_dir.glob("*.jpeg"))

    print(f"[CALIBRATE] Loading validation dataset from {val_dir} ...")
    print(f"            Found {len(real_images)} real images, {len(ai_images)} AI images.")

    y_true = []
    y_prob = []

    for img_p in real_images:
        res = detect_image(img_p)
        fused = fuse_predictions(res)
        y_true.append(0)
        y_prob.append(fused["ai_probability"])

    for img_p in ai_images:
        res = detect_image(img_p)
        fused = fuse_predictions(res)
        y_true.append(1)
        y_prob.append(fused["ai_probability"])

    # Grid search optimal thresholds
    best_f1 = -1.0
    best_cfg = (0.35, 0.65)

    for r_th in np.linspace(0.20, 0.45, 11):
        for a_th in np.linspace(0.55, 0.80, 11):
            if r_th >= a_th:
                continue
            metrics = evaluate_thresholds(y_true, y_prob, r_th, a_th)
            # Optimize F1 while penalizing high undetermined rates (>15%)
            score = metrics["f1"] - (metrics["undetermined_rate"] * 0.3)
            if score > best_f1:
                best_f1 = score
                best_cfg = (float(r_th), float(a_th))

    opt_metrics = evaluate_thresholds(y_true, y_prob, best_cfg[0], best_cfg[1])
    print(f"\n[OPTIMAL THRESHOLDS FOUND]")
    print(f"  REAL_THRESHOLD = {best_cfg[0]:.2f}")
    print(f"  AI_THRESHOLD   = {best_cfg[1]:.2f}")
    print(f"  Validation F1  = {opt_metrics['f1']:.4f}")
    print(f"  Accuracy       = {opt_metrics['accuracy']:.4f}")
    print(f"  Undetermined   = {opt_metrics['undetermined_rate']*100:.1f}%")

    if save:
        cfg = load_calibration_config()
        cfg["thresholds"]["real_threshold"] = round(best_cfg[0], 2)
        cfg["thresholds"]["ai_threshold"] = round(best_cfg[1], 2)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print(f"  ✅ Saved updated calibration settings to {CONFIG_PATH}")

    return {
        "optimal_thresholds": {
            "real_threshold": best_cfg[0],
            "ai_threshold": best_cfg[1],
        },
        "metrics": opt_metrics,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate decision thresholds on validation data.")
    parser.add_argument("--data", type=str, default="data/dataset", help="Validation dataset directory (must have real/ and ai/ folders)")
    parser.add_argument("--save", action="store_true", help="Save calibrated thresholds to calibration_config.json")
    args = parser.parse_args()

    if os.path.exists(args.data):
        calibrate_on_dataset(args.data, save=args.save)
    else:
        print(f"Dataset path '{args.data}' not found. Run with a valid dataset directory.")
