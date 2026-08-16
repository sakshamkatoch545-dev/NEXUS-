"""
evaluate.py
============
Performance evaluation (requirement #10), robustness testing under benign
transformations (requirement #9), and unseen-generator evaluation
(requirement #11).

Usage:
    python evaluate.py --root . --split test
    python evaluate.py --root . --split test --unseen-generators midjourney,dalle3
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from config import AppConfig, get_config
from detector import AIImageDetector
from preprocessing import UnsupportedImageError, apply_transform_for_robustness_test, prepare_image
from train import LABEL_AI, LABEL_HUMAN, Sample, _collect_samples, _infer_group

logger = logging.getLogger(__name__)

ROBUSTNESS_TRANSFORMS = [
    "jpeg_low",
    "resize_down_up",
    "crop",
    "brightness",
    "blur",
    "screenshot_like",
]


def _predict_batch(detector: AIImageDetector, samples: list, cfg: AppConfig) -> tuple[np.ndarray, np.ndarray]:
    y_true, y_prob = [], []
    for s in samples:
        try:
            result = detector.predict(s.path)
        except UnsupportedImageError:
            continue
        y_true.append(s.label)
        y_prob.append(result.ai_probability)
    return np.array(y_true), np.array(y_prob)


def _compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    if len(y_true) == 0:
        return {"error": "no samples evaluated"}
    y_pred = (y_prob >= threshold).astype(int)

    cm = confusion_matrix(y_true, y_pred, labels=[LABEL_HUMAN, LABEL_AI])
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else float("nan")
    fnr = fn / (fn + tp) if (fn + tp) > 0 else float("nan")

    metrics = {
        "n_samples": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_positive_rate": float(fpr),
        "false_negative_rate": float(fnr),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }
    if len(set(y_true.tolist())) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
    else:
        metrics["roc_auc"] = None
        metrics["warning"] = "ROC-AUC undefined: only one class present in this split."
    return metrics


def evaluate_split(detector: AIImageDetector, cfg: AppConfig, split_dir: Path) -> dict:
    samples = _collect_samples(split_dir, cfg)
    if not samples:
        return {"error": f"no samples found in {split_dir}"}
    y_true, y_prob = _predict_batch(detector, samples, cfg)
    return _compute_metrics(y_true, y_prob)


def evaluate_known_vs_unseen(
    detector: AIImageDetector, cfg: AppConfig, split_dir: Path, unseen_groups: set[str]
) -> dict:
    """Requirement #11: report performance separately for known vs unseen generators."""
    samples = _collect_samples(split_dir, cfg)
    known = [s for s in samples if s.label == LABEL_HUMAN or s.group not in unseen_groups]
    unseen = [s for s in samples if s.label == LABEL_AI and s.group in unseen_groups]

    results = {}
    for name, subset in (("known_generators", known), ("unseen_generators", unseen)):
        if not subset:
            results[name] = {"error": "no samples in this category"}
            continue
        y_true, y_prob = _predict_batch(detector, subset, cfg)
        results[name] = _compute_metrics(y_true, y_prob)
    return results


def evaluate_compressed_and_screenshots(detector: AIImageDetector, cfg: AppConfig, split_dir: Path) -> dict:
    """
    Requirement #11 (continued): separate reporting for compressed images and
    screenshots. We approximate this by applying the same benign transforms
    used in robustness testing and re-scoring, since a labeled
    compressed/screenshot subset may not exist in every dataset.
    """
    samples = _collect_samples(split_dir, cfg)
    results = {}
    for transform_name in ("jpeg_low", "screenshot_like"):
        y_true, y_prob = [], []
        for s in samples:
            try:
                prepared = prepare_image(s.path, cfg.preprocess)
                transformed = apply_transform_for_robustness_test(prepared, transform_name, cfg.preprocess)
            except UnsupportedImageError:
                continue
            fused, _ = detector.extract_features(_wrap_as_prepared(prepared, transformed))
            X = fused.reshape(1, -1)
            if detector._feature_scaler is not None:
                X = detector._feature_scaler.transform(X)
            if not detector._trained:
                continue
            proba = detector._calibrator.predict_proba(X)[0]
            y_true.append(s.label)
            y_prob.append(float(proba[1]))
        results[transform_name] = _compute_metrics(np.array(y_true), np.array(y_prob))
    return results


def _wrap_as_prepared(prepared, transformed_array):
    """Small helper: swap in a transformed array without duplicating PreparedImage logic."""
    from dataclasses import replace

    from PIL import Image

    pil = Image.fromarray((transformed_array * 255).astype("uint8"))
    return replace(prepared, analysis_rgb=transformed_array, analysis_pil=pil)


def evaluate_robustness(detector: AIImageDetector, cfg: AppConfig, split_dir: Path, max_samples: int = 40) -> dict:
    """
    Requirement #9: measure how much the AI-probability changes under
    benign transformations that should NOT flip a correct verdict.
    """
    samples = _collect_samples(split_dir, cfg)[:max_samples]
    per_transform_deltas: dict[str, list[float]] = {t: [] for t in ROBUSTNESS_TRANSFORMS}
    flips: dict[str, int] = {t: 0 for t in ROBUSTNESS_TRANSFORMS}
    evaluated = 0

    for s in samples:
        try:
            prepared = prepare_image(s.path, cfg.preprocess)
        except UnsupportedImageError:
            continue
        fused_orig, _ = detector.extract_features(prepared)
        X_orig = fused_orig.reshape(1, -1)
        if detector._feature_scaler is not None:
            X_orig = detector._feature_scaler.transform(X_orig)
        if not detector._trained:
            break
        base_prob = float(detector._calibrator.predict_proba(X_orig)[0][1])
        base_verdict = detector._verdict_from_probability(base_prob)
        evaluated += 1

        for transform_name in ROBUSTNESS_TRANSFORMS:
            transformed = apply_transform_for_robustness_test(prepared, transform_name, cfg.preprocess)
            wrapped = _wrap_as_prepared(prepared, transformed)
            fused_t, _ = detector.extract_features(wrapped)
            X_t = fused_t.reshape(1, -1)
            if detector._feature_scaler is not None:
                X_t = detector._feature_scaler.transform(X_t)
            new_prob = float(detector._calibrator.predict_proba(X_t)[0][1])
            new_verdict = detector._verdict_from_probability(new_prob)

            per_transform_deltas[transform_name].append(abs(new_prob - base_prob))
            if new_verdict != base_verdict:
                flips[transform_name] += 1

    summary = {}
    for t in ROBUSTNESS_TRANSFORMS:
        deltas = per_transform_deltas[t]
        summary[t] = {
            "mean_abs_probability_change": float(np.mean(deltas)) if deltas else None,
            "max_abs_probability_change": float(np.max(deltas)) if deltas else None,
            "verdict_flip_rate": (flips[t] / evaluated) if evaluated else None,
        }
    summary["n_base_images_evaluated"] = evaluated
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the AI-image detector.")
    parser.add_argument("--root", type=str, default=".")
    parser.add_argument("--split", type=str, default="test", choices=["train", "validation", "test"])
    parser.add_argument(
        "--unseen-generators", type=str, default="",
        help="Comma-separated group names (filename prefixes) to treat as unseen for requirement #11",
    )
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg: AppConfig = get_config(args.root)
    detector = AIImageDetector(cfg)

    split_dir = {"train": cfg.paths.train_dir, "validation": cfg.paths.validation_dir, "test": cfg.paths.test_dir}[
        args.split
    ]

    report: dict = {"split": args.split}
    report["overall_metrics"] = evaluate_split(detector, cfg, split_dir)

    unseen = {g.strip() for g in args.unseen_generators.split(",") if g.strip()}
    if unseen:
        report["known_vs_unseen"] = evaluate_known_vs_unseen(detector, cfg, split_dir, unseen)

    report["compressed_and_screenshot_metrics"] = evaluate_compressed_and_screenshots(detector, cfg, split_dir)
    report["robustness_to_benign_transforms"] = evaluate_robustness(detector, cfg, split_dir)

    cfg.paths.results_dir.mkdir(parents=True, exist_ok=True)
    out_path = cfg.paths.results_dir / f"evaluation_{args.split}.json"
    out_path.write_text(json.dumps(report, indent=2))

    print(json.dumps(report, indent=2))
    print(f"\nFull report written to {out_path}")
    print(
        "\nReminder: these numbers describe performance on THIS dataset only. "
        "They are not a general accuracy claim and do not represent equivalence "
        "to any third-party detector."
    )


if __name__ == "__main__":
    main()
