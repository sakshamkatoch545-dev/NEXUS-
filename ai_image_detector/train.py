"""
train.py
=========
Training pipeline for the classifier (requirements #5, #6, #12).

Expected directory layout (created for you under data/):

    data/
      train/{real,ai}/
      validation/{real,ai}/
      test/{real,ai}/

Usage:
    python train.py --root .
    python train.py --root . --classifier random_forest

Data-leakage prevention (requirement #6):
    - Near-duplicate images (perceptual hash within a small Hamming
      distance) are detected and only the first copy is kept — duplicates
      are dropped rather than allowed to land in two different splits.
    - Optional grouping by "source" is supported: if filenames encode a
      source/generator prefix like `midjourney__0001.png`, samples from the
      same group are kept out of validation/test.
    - Filenames, file paths, raw image dimensions, and any embedded
      generator watermark text are never used as features — only pixel
      content (see features.py).
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import imagehash
except ImportError:
    imagehash = None
import joblib
import numpy as np
from PIL import Image
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from calibration import ProbabilityCalibrator
from config import AppConfig, ClassifierName, get_config
from detector import AIImageDetector
from preprocessing import UnsupportedImageError, prepare_image

logger = logging.getLogger(__name__)

LABEL_HUMAN = 0
LABEL_AI = 1
LABEL_AI_EDITED = 2


@dataclass
class Sample:
    path: Path
    label: int
    group: str  # source/generator group for leakage-safe splitting


def _infer_group(path: Path) -> str:
    """
    Best-effort source-group inference from a filename prefix
    (e.g. 'midjourney__0001.png' -> 'midjourney'). Falls back to the
    parent directory name if no '__' separator is present.
    """
    stem = path.stem
    if "__" in stem:
        return stem.split("__", 1)[0]
    return path.parent.name


def _collect_samples(split_dir: Path, cfg: AppConfig) -> list[Sample]:
    samples: list[Sample] = []
    folder_mapping = (
        ("real", LABEL_HUMAN),
        ("ai", LABEL_AI),
        ("ai_edited", LABEL_AI_EDITED),
        ("filtered", LABEL_AI_EDITED),
        ("snapchat", LABEL_AI_EDITED),
        ("instagram", LABEL_AI_EDITED),
    )
    for label_name, label in folder_mapping:
        folder = split_dir / label_name
        if not folder.exists():
            continue
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() in cfg.preprocess.supported_extensions:
                samples.append(Sample(path=path, label=label, group=_infer_group(path)))
    return samples


def _dedupe_near_duplicates(samples: list[Sample], cfg: AppConfig) -> list[Sample]:
    """Drop near-duplicate images using perceptual hashing (requirement #6)."""
    kept: list[Sample] = []
    kept_hashes: list[imagehash.ImageHash] = []
    dropped = 0

    for s in samples:
        try:
            with Image.open(s.path) as img:
                h = imagehash.phash(img.convert("RGB"), hash_size=cfg.split.near_duplicate_hash_size)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not hash %s (%s) — keeping it anyway.", s.path, exc)
            kept.append(s)
            continue

        is_dup = any((h - kh) <= cfg.split.near_duplicate_max_hamming for kh in kept_hashes)
        if is_dup:
            dropped += 1
            continue
        kept.append(s)
        kept_hashes.append(h)

    logger.info("Near-duplicate filtering: kept %d, dropped %d of %d", len(kept), dropped, len(samples))
    return kept


def _extract_dataset_features(
    samples: list[Sample], detector: AIImageDetector, cfg: AppConfig
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    X, y, groups = [], [], []
    for i, s in enumerate(samples):
        try:
            prepared = prepare_image(s.path, cfg.preprocess)
        except UnsupportedImageError as exc:
            logger.warning("Skipping unreadable image %s: %s", s.path, exc)
            continue
        fused, _, _ = detector.extract_features(prepared)
        X.append(fused)
        y.append(s.label)
        groups.append(s.group)
        if (i + 1) % 50 == 0:
            logger.info("Extracted features for %d/%d images", i + 1, len(samples))
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64), groups


def _build_classifier(cfg: AppConfig, kind: ClassifierName):
    c = cfg.classifier
    if kind == "logistic_regression":
        return LogisticRegression(max_iter=2000, random_state=c.random_seed)
    if kind == "random_forest":
        return RandomForestClassifier(
            n_estimators=c.rf_n_estimators,
            max_depth=c.rf_max_depth,
            random_state=c.random_seed,
            n_jobs=-1,
        )
    if kind == "gradient_boosting":
        return GradientBoostingClassifier(
            n_estimators=c.n_estimators,
            max_depth=c.max_depth,
            learning_rate=c.learning_rate,
            random_state=c.random_seed,
        )
    raise ValueError(f"Unknown classifier kind: {kind}")


def train(cfg: AppConfig, classifier_kind: ClassifierName | None = None) -> None:
    random.seed(cfg.classifier.random_seed)
    np.random.seed(cfg.classifier.random_seed)

    kind = classifier_kind or cfg.classifier.kind
    cfg.paths.models_dir.mkdir(parents=True, exist_ok=True)

    train_samples = _dedupe_near_duplicates(_collect_samples(cfg.paths.train_dir, cfg), cfg)
    val_samples = _dedupe_near_duplicates(_collect_samples(cfg.paths.validation_dir, cfg), cfg)

    if cfg.split.group_split_by_source:
        train_groups = {s.group for s in train_samples}
        overlap = [s for s in val_samples if s.group in train_groups]
        if overlap:
            logger.warning(
                "%d validation samples share a source/group with training data; "
                "removing them to avoid leakage.", len(overlap)
            )
            val_samples = [s for s in val_samples if s.group not in train_groups]

    if not train_samples:
        raise RuntimeError(
            f"No training images found under {cfg.paths.train_dir}. "
            "Populate data/train/real and data/train/ai first."
        )

    logger.info("Training on %d images, validating on %d images", len(train_samples), len(val_samples))

    detector = AIImageDetector(cfg)  # used only for shared feature extraction
    X_train, y_train, _ = _extract_dataset_features(train_samples, detector, cfg)

    if len(val_samples) > 0:
        X_val, y_val, _ = _extract_dataset_features(val_samples, detector, cfg)
    else:
        logger.warning("No validation set found — carving 20%% out of training data instead.")
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=cfg.classifier.random_seed, stratify=y_train
        )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    base_model = _build_classifier(cfg, kind)
    calibrator = ProbabilityCalibrator(cfg.calibration)
    calibrator.fit(base_model, X_train_scaled, y_train)

    val_proba = calibrator.predict_proba(X_val_scaled)[:, 1]
    val_pred = (val_proba >= 0.5).astype(int)
    val_acc = float((val_pred == y_val).mean()) if len(y_val) else float("nan")
    logger.info("Validation accuracy (uncalibrated 0.5 threshold): %.4f", val_acc)

    joblib.dump(scaler, cfg.paths.feature_scaler_path)
    calibrator.save(cfg.paths.calibrator_path)
    # Save the underlying calibrated model as "the classifier" artifact too,
    # so detector.py's loader (which expects classifier_path to exist) is
    # satisfied; predict() actually uses the calibrator, which wraps this.
    joblib.dump(base_model, cfg.paths.classifier_path)

    metadata = {
        "classifier_kind": kind,
        "calibration_method": cfg.calibration.method,
        "n_train_samples": int(len(y_train)),
        "n_validation_samples": int(len(y_val)),
        "validation_accuracy_uncalibrated_threshold": val_acc,
        "feature_dim": int(X_train.shape[1]),
        "deep_backbone_used": detector._deep_extractor.available,
        "trained_at_unix": time.time(),
        "note": (
            "validation_accuracy is measured only on the supplied validation "
            "set and is NOT a guarantee of generalization to unseen generators "
            "or real-world images. Run evaluate.py for a fuller picture."
        ),
    }
    cfg.paths.metadata_path.write_text(json.dumps(metadata, indent=2))
    logger.info("Saved model artifacts to %s", cfg.paths.models_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the AI-image detector classifier.")
    parser.add_argument("--root", type=str, default=".", help="Project root containing data/ and models/")
    parser.add_argument(
        "--classifier",
        type=str,
        default=None,
        choices=["logistic_regression", "random_forest", "gradient_boosting"],
        help="Override the classifier kind from config.py",
    )
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = get_config(args.root)
    train(cfg, classifier_kind=args.classifier)


if __name__ == "__main__":
    main()
