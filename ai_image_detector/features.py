"""
features.py
============
Feature extraction: hand-crafted forensic features (requirement #2) plus an
optional deep-embedding branch from a pretrained open vision backbone
(requirement #3). All forensic features are original, standard, publicly
documented signal-processing / statistics computations (FFT, DCT, gradient
statistics, entropy, noise residuals, etc.) — nothing here is derived from
or specific to any proprietary detector.

The extractor NEVER uses filenames, file paths, image dimensions, or
embedded generator watermarks as features (requirement #6), only pixel
content.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from typing import Optional

import numpy as np
from scipy import fftpack, stats
from scipy.ndimage import laplace, sobel

from config import DeepFeatureConfig

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Forensic (hand-crafted) features
# --------------------------------------------------------------------------

@dataclass
class ForensicFeatures:
    # RGB statistics
    r_mean: float; g_mean: float; b_mean: float
    r_std: float; g_std: float; b_std: float
    r_skew: float; g_skew: float; b_skew: float
    r_kurtosis: float; g_kurtosis: float; b_kurtosis: float

    # Luminance statistics
    luminance_mean: float
    luminance_std: float
    luminance_entropy: float

    # Local contrast / texture
    local_contrast_mean: float
    local_contrast_std: float
    texture_energy: float  # GLCM-like second-moment proxy via local variance

    # Edges
    edge_density: float
    edge_strength_mean: float
    edge_strength_std: float

    # Laplacian (sharpness / focus proxy, sensitive to over-smooth AI textures)
    laplacian_var: float
    laplacian_mean_abs: float

    # Noise residual (high-pass minus denoised)
    noise_residual_mean: float
    noise_residual_std: float
    noise_residual_entropy: float

    # Frequency domain (FFT)
    fft_high_freq_energy_ratio: float
    fft_low_freq_energy_ratio: float
    fft_radial_slope: float  # slope of log power vs log frequency (1/f falloff)

    # DCT / JPEG-related (8x8 block DCT, mimics JPEG's own transform)
    dct_high_freq_energy_ratio: float
    dct_block_boundary_discontinuity: float  # blockiness indicator

    # Color-channel relationships
    rg_correlation: float
    gb_correlation: float
    rb_correlation: float
    color_channel_std_ratio: float

    # Local smoothness
    smoothness_index: float  # fraction of near-zero local gradients

    # Repeated-pattern indicator (self-similarity via autocorrelation peak)
    repetition_score: float

    def as_vector(self) -> np.ndarray:
        return np.array([getattr(self, f.name) for f in fields(self)], dtype=np.float32)

    @staticmethod
    def names() -> list[str]:
        return [f.name for f in fields(ForensicFeatures)]


def _entropy(channel: np.ndarray, bins: int = 256) -> float:
    hist, _ = np.histogram(channel, bins=bins, range=(0.0, 1.0), density=True)
    hist = hist[hist > 0]
    return float(stats.entropy(hist))


def _radial_fft_slope(magnitude: np.ndarray) -> tuple[float, float, float]:
    """Return (high_freq_ratio, low_freq_ratio, radial_slope) from a 2D FFT magnitude."""
    h, w = magnitude.shape
    cy, cx = h // 2, w // 2
    y, x = np.ogrid[:h, :w]
    r = np.sqrt((y - cy) ** 2 + (x - cx) ** 2).astype(np.int32)
    max_r = r.max()
    radial_sum = np.bincount(r.ravel(), weights=magnitude.ravel(), minlength=max_r + 1)
    radial_count = np.bincount(r.ravel(), minlength=max_r + 1)
    radial_mean = radial_sum / np.maximum(radial_count, 1)

    total_energy = radial_sum.sum() + 1e-8
    low_cut = max_r // 6
    high_cut = max_r // 2
    low_energy = radial_sum[:low_cut].sum() / total_energy
    high_energy = radial_sum[high_cut:].sum() / total_energy

    # log-log slope over the mid-frequency band, robust to DC spike
    freqs = np.arange(1, max_r + 1)
    valid = (freqs > 2) & (radial_mean[1:] > 0)
    if valid.sum() > 5:
        log_f = np.log(freqs[valid])
        log_p = np.log(radial_mean[1:][valid] + 1e-8)
        slope = float(np.polyfit(log_f, log_p, 1)[0])
    else:
        slope = 0.0
    return float(high_energy), float(low_energy), slope


def _block_dct_features(gray: np.ndarray) -> tuple[float, float]:
    """8x8 block DCT to mirror JPEG's own transform domain."""
    h, w = gray.shape
    h8, w8 = (h // 8) * 8, (w // 8) * 8
    g = gray[:h8, :w8]
    blocks = g.reshape(h8 // 8, 8, w8 // 8, 8).transpose(0, 2, 1, 3)  # (nby, nbx, 8, 8)
    dct_blocks = fftpack.dctn(blocks, axes=(2, 3), norm="ortho")

    energy = np.abs(dct_blocks)
    total = energy.sum() + 1e-8
    high_freq_mask = np.zeros((8, 8), dtype=bool)
    high_freq_mask[4:, 4:] = True
    high_energy = energy[:, :, high_freq_mask].sum() / total

    # Blockiness: discontinuity across 8x8 block boundaries vs within blocks
    vert_boundary = np.abs(np.diff(g[:, 7::8], axis=0)).mean() if g.shape[0] > 8 else 0.0
    vert_interior = np.abs(np.diff(g, axis=0)).mean() + 1e-8
    blockiness = float(vert_boundary / vert_interior)

    return float(high_energy), blockiness


def _autocorrelation_repetition_score(gray: np.ndarray) -> float:
    """Detects unnaturally strong periodic/repeated texture via autocorrelation side-lobes."""
    g = gray - gray.mean()
    f = np.fft.fft2(g)
    power = np.abs(f) ** 2
    autocorr = np.fft.ifft2(power).real
    autocorr = np.fft.fftshift(autocorr)
    autocorr /= autocorr.max() + 1e-8

    h, w = autocorr.shape
    cy, cx = h // 2, w // 2
    center_region = autocorr[cy - 2:cy + 3, cx - 2:cx + 3].copy()
    center_region[2, 2] = 0  # zero out the zero-lag peak
    return float(np.clip(center_region.max(), 0.0, 1.0))


def extract_forensic_features(rgb: np.ndarray) -> ForensicFeatures:
    """
    rgb: float32 array in [0, 1], shape (H, W, 3).
    Only pixel content is used — no filenames, dims, or metadata.
    """
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    gray = 0.299 * r + 0.587 * g + 0.114 * b

    # Local contrast via sliding window std (cheap box-filter approximation)
    from scipy.ndimage import uniform_filter

    local_mean = uniform_filter(gray, size=7)
    local_sqmean = uniform_filter(gray**2, size=7)
    local_var = np.clip(local_sqmean - local_mean**2, 0, None)
    local_contrast = np.sqrt(local_var)

    grad_x = sobel(gray, axis=1)
    grad_y = sobel(gray, axis=0)
    grad_mag = np.hypot(grad_x, grad_y)
    edge_thresh = grad_mag.mean() + grad_mag.std()
    edge_density = float((grad_mag > edge_thresh).mean())

    lap = laplace(gray)

    # Simple denoise-and-subtract residual (median filter as the denoiser)
    from scipy.ndimage import median_filter

    denoised = median_filter(gray, size=3)
    residual = gray - denoised

    fft_mag = np.abs(np.fft.fftshift(np.fft.fft2(gray)))
    high_ratio, low_ratio, radial_slope = _radial_fft_slope(fft_mag)

    dct_high_ratio, blockiness = _block_dct_features(gray)

    repetition_score = _autocorrelation_repetition_score(gray)

    channel_stds = np.array([r.std(), g.std(), b.std()]) + 1e-8

    return ForensicFeatures(
        r_mean=float(r.mean()), g_mean=float(g.mean()), b_mean=float(b.mean()),
        r_std=float(r.std()), g_std=float(g.std()), b_std=float(b.std()),
        r_skew=float(stats.skew(r.ravel())), g_skew=float(stats.skew(g.ravel())), b_skew=float(stats.skew(b.ravel())),
        r_kurtosis=float(stats.kurtosis(r.ravel())), g_kurtosis=float(stats.kurtosis(g.ravel())), b_kurtosis=float(stats.kurtosis(b.ravel())),
        luminance_mean=float(gray.mean()),
        luminance_std=float(gray.std()),
        luminance_entropy=_entropy(gray),
        local_contrast_mean=float(local_contrast.mean()),
        local_contrast_std=float(local_contrast.std()),
        texture_energy=float(local_var.mean()),
        edge_density=edge_density,
        edge_strength_mean=float(grad_mag.mean()),
        edge_strength_std=float(grad_mag.std()),
        laplacian_var=float(lap.var()),
        laplacian_mean_abs=float(np.abs(lap).mean()),
        noise_residual_mean=float(residual.mean()),
        noise_residual_std=float(residual.std()),
        noise_residual_entropy=_entropy((residual - residual.min()) / (np.ptp(residual) + 1e-8)),
        fft_high_freq_energy_ratio=high_ratio,
        fft_low_freq_energy_ratio=low_ratio,
        fft_radial_slope=radial_slope,
        dct_high_freq_energy_ratio=dct_high_ratio,
        dct_block_boundary_discontinuity=blockiness,
        rg_correlation=float(np.corrcoef(r.ravel(), g.ravel())[0, 1]),
        gb_correlation=float(np.corrcoef(g.ravel(), b.ravel())[0, 1]),
        rb_correlation=float(np.corrcoef(r.ravel(), b.ravel())[0, 1]),
        color_channel_std_ratio=float(channel_stds.max() / channel_stds.min()),
        smoothness_index=float((grad_mag < (0.02)).mean()),
        repetition_score=repetition_score,
    )


# --------------------------------------------------------------------------
# Deep visual embeddings (optional, graceful fallback)
# --------------------------------------------------------------------------

class DeepFeatureExtractor:
    """
    Wraps a pretrained open vision backbone (default: CLIP ViT-B/32) to
    produce a fixed-length embedding per image. If the model/weights can't
    be loaded (no internet, package missing, etc.) this degrades gracefully:
    `available` becomes False and callers fall back to forensic-only mode.
    """

    def __init__(self, cfg: DeepFeatureConfig):
        self.cfg = cfg
        self.available = False
        self._model = None
        self._processor = None
        if cfg.enabled:
            self._try_load()

    def _try_load(self) -> None:
        try:
            import torch  # noqa: F401
            from transformers import CLIPModel, CLIPProcessor

            self._processor = CLIPProcessor.from_pretrained(self.cfg.model_name)
            self._model = CLIPModel.from_pretrained(self.cfg.model_name)
            self._model.to(self.cfg.device)
            self._model.eval()
            self.available = True
            logger.info("Deep feature backbone '%s' loaded.", self.cfg.model_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Deep feature backbone unavailable (%s). "
                "Falling back to forensic-features-only mode.", exc
            )
            self.available = False
            self._model = None
            self._processor = None

    def embed(self, pil_image) -> Optional[np.ndarray]:
        if not self.available:
            return None
        try:
            import torch

            inputs = self._processor(images=pil_image, return_tensors="pt").to(self.cfg.device)
            with torch.no_grad():
                feats = self._model.get_image_features(**inputs)
            if hasattr(feats, "pooler_output") and feats.pooler_output is not None:
                feats = feats.pooler_output
            elif hasattr(feats, "last_hidden_state") and feats.last_hidden_state is not None:
                feats = feats.last_hidden_state[:, 0, :]
            elif not hasattr(feats, "squeeze") and hasattr(feats, "__getitem__"):
                feats = feats[0]
            vec = feats.squeeze().cpu().numpy().astype(np.float32)
            norm = np.linalg.norm(vec) + 1e-8
            return vec / norm
        except Exception as exc:  # noqa: BLE001
            logger.warning("Deep embedding extraction failed for one image: %s", exc)
            return None


def fuse_features(
    forensic: ForensicFeatures,
    deep_embedding: Optional[np.ndarray],
    deep_dim: int,
) -> np.ndarray:
    """
    Feature fusion (architecture step): concatenate forensic vector with the
    deep embedding. If the deep embedding is unavailable, zero-pad and rely
    on the forensic branch — the classifier is trained the same way so this
    is a valid degraded mode, not an error state.
    """
    forensic_vec = forensic.as_vector()
    if deep_embedding is None:
        deep_vec = np.zeros(deep_dim, dtype=np.float32)
    else:
        deep_vec = deep_embedding
    return np.concatenate([forensic_vec, deep_vec], axis=0)


def detect_local_ai_manipulation(
    rgb: np.ndarray,
    grid_size: tuple[int, int] = (4, 4),
) -> dict:
    """
    Analyze localized spatial inconsistency to detect images that are
    GENUINE/REAL overall but have been PARTIALLY EDITED, INPAINTED,
    FACE-SWAPPED, or ENHANCED by AI (like ZeroGPT / GPTZero image forensics).

    Key Forensic Principles:
    1. Uniform Sensor Noise vs Localized Denoising: Natural camera sensors deposit
    Extract localized inpainting, editing, and manipulation forensic features.
    Uses robust multi-tile wavelet noise estimation and normalized noise-to-texture ratios.
    """
    import pywt
    from scipy.ndimage import laplace
    import scipy.stats as stats

    h, w, _ = image_np.shape
    r = image_np[..., 0].astype(np.float32)
    g = image_np[..., 1].astype(np.float32)
    b = image_np[..., 2].astype(np.float32)
    gray = 0.299 * r + 0.587 * g + 0.114 * b

    rows, cols = grid_size
    tile_h, tile_w = max(4, h // rows), max(4, w // cols)

    tile_noise = []
    tile_ratio = []

    for r_idx in range(rows):
        for c_idx in range(cols):
            y0, y1 = r_idx * tile_h, (r_idx + 1) * tile_h
            x0, x1 = c_idx * tile_w, (c_idx + 1) * tile_w
            tile_gray = gray[y0:y1, x0:x1]

            coeffs = pywt.dwt2(tile_gray, 'db4')
            _, (_, _, hh) = coeffs
            sigma = float(np.median(np.abs(hh)) / 0.6745)
            l_var = float(laplace(tile_gray).var())

            tile_noise.append(sigma)
            tile_ratio.append(sigma / (np.sqrt(l_var) + 1e-4))

    n_arr = np.array(tile_noise, dtype=np.float32)
    r_arr = np.array(tile_ratio, dtype=np.float32)

    n_med = float(np.median(n_arr))
    n_iqr = float(stats.iqr(n_arr)) + 1e-5
    n_z = np.abs(n_arr - n_med) / n_iqr

    r_med = float(np.median(r_arr))
    r_iqr = float(stats.iqr(r_arr)) + 1e-5
    r_z = np.abs(r_arr - r_med) / r_iqr

    anomalous_patches = int(np.sum((n_z > 3.5) & (r_z > 3.0)))
    max_nz = float(np.max(n_z))
    max_rz = float(np.max(r_z))
    total_patches = rows * cols

    is_edited = bool(anomalous_patches >= 1 and max_nz >= 4.0 and max_rz >= 3.2)
    if is_edited:
        manipulation_score = float(np.clip(max_nz * 12.0, 65.0, 100.0))
        ai_edited_prob = float(1.0 / (1.0 + np.exp(-(manipulation_score - 45.0) / 8.0)))
    else:
        manipulation_score = float(np.clip(min(max_rz, 2.5) * 6.0, 0.0, 20.0))
        ai_edited_prob = float(1.0 / (1.0 + np.exp(-(manipulation_score - 45.0) / 8.0)))

    noise_cv = float(n_arr.std() / (n_arr.mean() + 1e-6))
    lap_cv = float(r_arr.std() / (r_arr.mean() + 1e-6))

    local_signals = []
    if is_edited:
        local_signals.append(f"localized AI inpainting / object removal detected ({anomalous_patches} anomaly patch(es), noise disparity z={max_nz:.2f})")
    if noise_cv > 0.60:
        local_signals.append("bimodal noise distribution: organic sensor grain with synthetic editing")

    # Snapchat / AR Filter heuristic
    # Extreme smoothness (low laplacian) across tiles combined with high variance in ratios can indicate beauty filters
    face_smoothing_score = 0.0
    ar_overlay_score = 0.0
    if r_med > 5.0 and lap_cv > 0.5:
        face_smoothing_score = float(np.clip((r_med - 5.0) * 10, 0, 100))
        local_signals.append("aggressive face smoothing or beauty filter detected (e.g. Snapchat/Instagram filter)")
        if not is_edited:
            ai_edited_prob = max(ai_edited_prob, face_smoothing_score / 100.0)
            manipulation_score = max(manipulation_score, face_smoothing_score)

    if n_med < 0.5 and noise_cv > 0.8:
        ar_overlay_score = float(np.clip(noise_cv * 50, 0, 100))
        local_signals.append("synthetic AR overlay or digital makeup detected")
        if not is_edited:
            ai_edited_prob = max(ai_edited_prob, ar_overlay_score / 100.0)
            manipulation_score = max(manipulation_score, ar_overlay_score)

    return {
        "manipulation_score": round(manipulation_score, 2),
        "ai_edited_probability": round(ai_edited_prob, 4),
        "suspected_anomalous_patches": anomalous_patches,
        "total_patches": total_patches,
        "noise_cv": round(noise_cv, 4),
        "sharpness_cv": round(lap_cv, 4),
        "face_smoothing_score": round(face_smoothing_score, 2),
        "ar_overlay_score": round(ar_overlay_score, 2),
        "local_signals": local_signals,
    }
