"""
calibration.py
===============
Probability calibration so the classifier's raw scores translate into
honest probabilities rather than overconfident 0.99 / 0.01 outputs
(requirement #7).

Supports Platt scaling (sigmoid) and isotonic regression, both fit via
cross-validated `CalibratedClassifierCV` from scikit-learn, which is the
standard, well-documented approach for this.
"""

from __future__ import annotations

import logging
from typing import Optional

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV

from config import CalibrationConfig

logger = logging.getLogger(__name__)


class ProbabilityCalibrator:
    """Thin wrapper so detector.py doesn't care which calibration method was used."""

    def __init__(self, cfg: CalibrationConfig):
        self.cfg = cfg
        self._calibrated_model = None

    def fit(self, base_estimator, X: np.ndarray, y: np.ndarray) -> "ProbabilityCalibrator":
        if self.cfg.method == "none":
            self._calibrated_model = base_estimator.fit(X, y)
            return self

        method = "sigmoid" if self.cfg.method == "platt" else "isotonic"
        n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
        safe_folds = max(2, min(self.cfg.cv_folds, n_pos, n_neg))
        if safe_folds < self.cfg.cv_folds:
            logger.warning(
                "Reducing calibration CV folds from %d to %d due to small class counts.",
                self.cfg.cv_folds, safe_folds,
            )

        self._calibrated_model = CalibratedClassifierCV(
            base_estimator, method=method, cv=safe_folds
        )
        self._calibrated_model.fit(X, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self._calibrated_model is None:
            raise RuntimeError("Calibrator has not been fit or loaded yet.")
        return self._calibrated_model.predict_proba(X)

    def save(self, path) -> None:
        joblib.dump(self._calibrated_model, path)

    def load(self, path) -> "ProbabilityCalibrator":
        self._calibrated_model = joblib.load(path)
        return self


def estimate_confidence(prob_ai: float) -> float:
    """
    Confidence = distance from the maximally-uncertain point (0.5), rescaled
    to [0, 1]. A prob of 0.5 -> confidence 0.0; a prob of 0.0 or 1.0 -> 1.0.
    This is intentionally conservative and independent of the classifier's
    own (often overconfident) internal margins.
    """
    return float(np.clip(abs(prob_ai - 0.5) * 2.0, 0.0, 1.0))
