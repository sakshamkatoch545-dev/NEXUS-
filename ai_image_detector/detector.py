"""
detector.py
============
Main entry point for inference.

    from detector import AIImageDetector
    detector = AIImageDetector()
    result = detector.predict("image.jpg")

This is an ORIGINAL implementation built from publicly documented,
general-purpose forensic image-analysis and machine-learning techniques
(FFT/DCT analysis, noise-residual statistics, pretrained vision embeddings,
calibrated classifiers). It does not copy, reverse-engineer, or claim
equivalence to any commercial product. See the module docstrings in
features.py, calibration.py, and README-level comments below for the
scientific caveats every result carries.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import joblib
import numpy as np

from calibration import ProbabilityCalibrator, estimate_confidence
from config import AppConfig, get_config
from features import (
    DeepFeatureExtractor,
    ForensicFeatures,
    detect_local_ai_manipulation,
    extract_forensic_features,
    fuse_features,
)
from preprocessing import PreparedImage, UnsupportedImageError, prepare_image

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    ai_probability: float
    human_probability: float
    ai_edited_probability: float = 0.0
    confidence: float = 0.0
    verdict: str = "UNCERTAIN"  # "AI" | "HUMAN" | "AI_EDITED" | "UNCERTAIN"
    is_ai_edited: bool = False
    manipulation_details: dict[str, Any] = field(default_factory=dict)
    signals: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# Human-readable descriptions for the strongest forensic signals, used for
# explainability (requirement #8). Kept intentionally hedged in language.
_SIGNAL_DESCRIPTIONS: dict[str, str] = {
    "fft_high_freq_energy_ratio": "atypical high-frequency energy distribution",
    "fft_radial_slope": "unusual frequency falloff (non-natural 1/f spectrum)",
    "dct_high_freq_energy_ratio": "atypical DCT high-frequency energy",
    "dct_block_boundary_discontinuity": "unusual JPEG block-boundary pattern",
    "noise_residual_std": "atypical noise-residual variance",
    "noise_residual_entropy": "unusual noise-residual entropy",
    "laplacian_var": "atypical fine-detail (sharpness) statistics",
    "texture_energy": "synthetic-looking texture uniformity",
    "smoothness_index": "unusually smooth local regions",
    "repetition_score": "repeated/self-similar texture pattern",
    "edge_density": "atypical edge density",
    "color_channel_std_ratio": "unusual inter-channel color relationship",
    "rg_correlation": "atypical red-green channel correlation",
    "gb_correlation": "atypical green-blue channel correlation",
    "rb_correlation": "atypical red-blue channel correlation",
}


class AIImageDetector:
    """
    High-level detector combining forensic + deep features, localized inpainting/edit
    analysis, a trained classifier, and probability calibration into a single `predict()` call.

    If no trained classifier exists on disk yet, the detector still loads
    and extracts forensic + spatial manipulation features with an explicit warning.
    """

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self._deep_extractor = DeepFeatureExtractor(self.config.deep)
        self._classifier = None
        self._calibrator: Optional[ProbabilityCalibrator] = None
        self._feature_scaler = None
        self._trained = False
        self._load_trained_artifacts()

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------
    def _load_trained_artifacts(self) -> None:
        paths = self.config.paths
        try:
            if paths.classifier_path.exists():
                self._classifier = joblib.load(paths.classifier_path)
            if paths.calibrator_path.exists():
                self._calibrator = ProbabilityCalibrator(self.config.calibration).load(
                    paths.calibrator_path
                )
            if paths.feature_scaler_path.exists():
                self._feature_scaler = joblib.load(paths.feature_scaler_path)
            self._trained = self._classifier is not None and self._calibrator is not None
            if self._trained:
                logger.info("Loaded trained classifier + calibrator from %s", paths.models_dir)
            else:
                logger.warning(
                    "No trained classifier found at %s. Run train.py first; "
                    "predict() will evaluate forensic & local manipulation signals "
                    "with heuristic fallback.", paths.models_dir
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load trained artifacts: %s", exc)
            self._trained = False

    # ------------------------------------------------------------------
    # Feature extraction (shared by inference + training pipelines)
    # ------------------------------------------------------------------
    def extract_features(
        self,
        prepared: PreparedImage,
        progress_cb: Optional[Callable[[int, str], None]] = None,
    ) -> tuple[np.ndarray, ForensicFeatures, dict]:
        if progress_cb:
            progress_cb(30, "Extracting forensic frequency & spectral statistics...")
        forensic = extract_forensic_features(prepared.analysis_rgb)

        if progress_cb:
            progress_cb(55, "Scanning for localized AI inpainting & generative edits...")
        manipulation = detect_local_ai_manipulation(prepared.analysis_rgb)

        if progress_cb:
            progress_cb(75, "Extracting deep visual representations (CLIP)...")
        deep_embedding = self._deep_extractor.embed(prepared.analysis_pil)

        fused = fuse_features(forensic, deep_embedding, self.config.deep.embedding_dim)
        return fused, forensic, manipulation

    # ------------------------------------------------------------------
    # Inference with Progress Callback
    # ------------------------------------------------------------------
    def predict(
        self,
        image: str | Path | bytes,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> DetectionResult:
        """
        Run comprehensive AI image detection with progress tracking.
        Detects 100% AI generated images, genuine human photos, and real images
        edited/retouched/inpainted by AI.
        """
        warnings: list[str] = []

        if progress_callback:
            progress_callback(10, "Preprocessing & format normalization...")

        try:
            prepared = prepare_image(image, self.config.preprocess)
        except UnsupportedImageError as exc:
            if progress_callback:
                progress_callback(100, "Failed: Unsupported image format.")
            return DetectionResult(
                ai_probability=0.0,
                human_probability=0.0,
                ai_edited_probability=0.0,
                confidence=0.0,
                verdict="UNCERTAIN",
                is_ai_edited=False,
                signals=[],
                warnings=[f"Could not process image: {exc}"],
            )

        if not self._deep_extractor.available:
            warnings.append(
                "Deep visual backbone unavailable — running on forensic & spatial features only. "
                "Accuracy may be reduced."
            )

        fused_vector, forensic, manipulation = self.extract_features(prepared, progress_callback)

        ai_edited_prob = manipulation.get("ai_edited_probability", 0.0)
        manip_score = manipulation.get("manipulation_score", 0.0)
        is_edited_flag = bool(
            ai_edited_prob >= self.config.verdict.ai_edited_threshold
            and manip_score >= self.config.verdict.min_manipulation_score
        )

        if progress_callback:
            progress_callback(90, "Synthesizing multi-modal features & calibrating verdict...")

        if not self._trained:
            # Fallback heuristic mode when classifier weights are not trained yet
            heuristic_ai_prob = 0.50
            if is_edited_flag and manip_score > 50.0:
                heuristic_ai_prob = 0.45
                verdict = "AI_EDITED"
            else:
                verdict = "UNCERTAIN"

            if progress_callback:
                progress_callback(100, "Analysis complete.")

            signals = self._top_signals(forensic) + manipulation.get("local_signals", [])
            return DetectionResult(
                ai_probability=heuristic_ai_prob,
                human_probability=round(1.0 - heuristic_ai_prob, 4),
                ai_edited_probability=round(ai_edited_prob, 4),
                confidence=round(manip_score / 100.0 if is_edited_flag else 0.0, 4),
                verdict=verdict,
                is_ai_edited=is_edited_flag,
                manipulation_details=manipulation,
                signals=signals,
                warnings=warnings + [
                    "No trained classifier is loaded. This result is based on forensic heuristics. "
                    "Run train.py to fit a model on your own labeled dataset before trusting any verdict."
                ],
            )

        X = fused_vector.reshape(1, -1)
        if self._feature_scaler is not None:
            X = self._feature_scaler.transform(X)

        proba = self._calibrator.predict_proba(X)[0]
        # class 1 == "AI", class 0 == "HUMAN" by convention (see train.py)
        ai_prob = float(proba[1])
        human_prob = float(proba[0])
        confidence = estimate_confidence(ai_prob)

        verdict = self._verdict_from_probability(ai_prob, ai_edited_prob, manip_score)
        signals = self._top_signals(forensic) + manipulation.get("local_signals", [])

        if is_edited_flag and verdict == "AI_EDITED":
            signals.insert(0, "localized spatial inconsistency (real photograph with AI generative inpainting / edit)")

        if confidence < self.config.verdict.min_confidence_to_report_signal:
            warnings.append("Low-confidence prediction — treat signals as exploratory only.")

        warnings.append(
            "This is a statistical estimate based on forensic signal processing and machine learning. "
            "It is not proof of image origin and can be affected by extreme compression or aggressive artistic filters."
        )

        if progress_callback:
            progress_callback(100, "Analysis complete.")

        return DetectionResult(
            ai_probability=round(ai_prob, 4),
            human_probability=round(human_prob, 4),
            ai_edited_probability=round(ai_edited_prob, 4),
            confidence=round(confidence, 4),
            verdict=verdict,
            is_ai_edited=(verdict == "AI_EDITED" or is_edited_flag),
            manipulation_details=manipulation,
            signals=signals,
            warnings=warnings,
        )

    def _verdict_from_probability(
        self,
        ai_prob: float,
        ai_edited_prob: float,
        manip_score: float,
    ) -> str:
        v = self.config.verdict
        # 1. Clear fully-AI image
        if ai_prob >= v.ai_threshold:
            return "AI"

        # 2. Base human photo, check if edited by AI
        if ai_prob <= v.human_threshold:
            if ai_edited_prob >= v.ai_edited_threshold and manip_score >= v.min_manipulation_score:
                return "AI_EDITED"
            return "HUMAN"

        # 3. Borderline cases: if strong local inpainting/editing anomaly detected, flag AI_EDITED
        if ai_edited_prob >= 0.60 and manip_score >= 45.0:
            return "AI_EDITED"

        return "UNCERTAIN"

    def _top_signals(self, forensic: ForensicFeatures, top_k: int = 3) -> list[str]:
        """
        Explainability: report the forensic features that are most extreme
        relative to typical natural-photo ranges (requirement #8).
        """
        reference_mid = {
            "fft_high_freq_energy_ratio": 0.08,
            "fft_radial_slope": -1.8,
            "dct_high_freq_energy_ratio": 0.05,
            "dct_block_boundary_discontinuity": 1.0,
            "noise_residual_std": 0.02,
            "noise_residual_entropy": 4.0,
            "laplacian_var": 0.02,
            "texture_energy": 0.01,
            "smoothness_index": 0.5,
            "repetition_score": 0.15,
            "edge_density": 0.12,
            "color_channel_std_ratio": 1.1,
            "rg_correlation": 0.85,
            "gb_correlation": 0.85,
            "rb_correlation": 0.75,
        }
        scores = []
        for name, mid in reference_mid.items():
            val = getattr(forensic, name, None)
            if val is None:
                continue
            deviation = abs(val - mid) / (abs(mid) + 1e-3)
            scores.append((deviation, name))
        scores.sort(reverse=True)

        signals = []
        for _, name in scores[:top_k]:
            desc = _SIGNAL_DESCRIPTIONS.get(name, name)
            signals.append(desc)
        return signals


def _cli_progress_bar(pct: int, msg: str) -> None:
    bar_len = 25
    filled = int(bar_len * pct / 100)
    bar = "=" * filled + "-" * (bar_len - filled)
    sys.stdout.write(f"\r[{bar}] {pct:3d}% | {msg:<50}")
    sys.stdout.flush()
    if pct >= 100:
        sys.stdout.write("\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    if len(sys.argv) < 2:
        print("Usage: python detector.py <image_path>")
        sys.exit(1)

    print(f"\n[SCAN] Analyzing image: {sys.argv[1]}")
    detector = AIImageDetector()
    result = detector.predict(sys.argv[1], progress_callback=_cli_progress_bar)
    print("\n--- RESULTS ---")
    print(result.to_json(indent=2))

