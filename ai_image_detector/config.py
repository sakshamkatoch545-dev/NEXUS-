"""
config.py
=========
Central configuration for the AI-image detector project.

All paths are relative to a configurable project root (defaults to the
current working directory) so nothing is hard-coded to a particular
machine. Every other module imports its settings from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ClassifierName = Literal["logistic_regression", "random_forest", "gradient_boosting"]
CalibrationName = Literal["platt", "isotonic", "none"]


@dataclass(frozen=True)
class PathConfig:
    """Filesystem layout. Override `root` to point anywhere you like."""

    root: Path = field(default_factory=lambda: Path.cwd())

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def train_dir(self) -> Path:
        return self.data_dir / "train"

    @property
    def validation_dir(self) -> Path:
        return self.data_dir / "validation"

    @property
    def test_dir(self) -> Path:
        return self.data_dir / "test"

    @property
    def models_dir(self) -> Path:
        return self.root / "models"

    @property
    def results_dir(self) -> Path:
        return self.root / "results"

    @property
    def classifier_path(self) -> Path:
        return self.models_dir / "classifier.joblib"

    @property
    def calibrator_path(self) -> Path:
        return self.models_dir / "calibrator.joblib"

    @property
    def feature_scaler_path(self) -> Path:
        return self.models_dir / "feature_scaler.joblib"

    @property
    def metadata_path(self) -> Path:
        return self.models_dir / "model_metadata.json"


@dataclass(frozen=True)
class PreprocessConfig:
    target_size: tuple[int, int] = (256, 256)
    supported_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp")
    # JPEG re-compression sweep used to make features compression-aware.
    jpeg_quality_probe_levels: tuple[int, ...] = (95, 75, 50)


@dataclass(frozen=True)
class DeepFeatureConfig:
    # Any open, publicly documented backbone works here; CLIP ViT-B/32 is
    # used as the default because weights are small and widely available.
    model_name: str = "openai/clip-vit-base-patch32"
    embedding_dim: int = 512
    device: str = "cpu"
    enabled: bool = True  # gracefully disabled at runtime if load fails


@dataclass(frozen=True)
class ClassifierConfig:
    kind: ClassifierName = "gradient_boosting"
    random_seed: int = 42
    n_estimators: int = 300
    max_depth: int = 4
    learning_rate: float = 0.05
    rf_n_estimators: int = 400
    rf_max_depth: int | None = 12


@dataclass(frozen=True)
class CalibrationConfig:
    method: CalibrationName = "isotonic"
    cv_folds: int = 5


@dataclass(frozen=True)
class VerdictConfig:
    ai_threshold: float = 0.65
    human_threshold: float = 0.35
    ai_edited_threshold: float = 0.50  # probability threshold to flag real-but-AI-edited
    min_manipulation_score: float = 35.0  # patch-level inconsistency score threshold
    # Anything between human_threshold and ai_threshold -> "UNCERTAIN"
    min_confidence_to_report_signal: float = 0.15


@dataclass(frozen=True)
class DataSplitConfig:
    # Data-leakage controls (see requirements #6).
    near_duplicate_hash_size: int = 16  # perceptual hash size
    near_duplicate_max_hamming: int = 4  # hashes within this distance = duplicates
    group_split_by_source: bool = True


@dataclass(frozen=True)
class AppConfig:
    paths: PathConfig = field(default_factory=PathConfig)
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    deep: DeepFeatureConfig = field(default_factory=DeepFeatureConfig)
    classifier: ClassifierConfig = field(default_factory=ClassifierConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    verdict: VerdictConfig = field(default_factory=VerdictConfig)
    split: DataSplitConfig = field(default_factory=DataSplitConfig)
    log_level: str = "INFO"


def get_config(root: Path | str | None = None) -> AppConfig:
    """Factory so callers can point the whole pipeline at a custom root dir."""
    if root is None:
        return AppConfig()
    return AppConfig(paths=PathConfig(root=Path(root)))
