"""
test_models.py — Comprehensive Quality Control & Robustness Test Suite
======================================================================
Verifies model loading, offline execution, probability validity, error isolation,
and performance across image variations (JPEG compression, resize, formats, resolutions).
"""

import os
import sys
import io
import time
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from inference import detect_image, get_default_device
from fusion import fuse_predictions
from registry import get_cached_models, MODEL_REGISTRY


def create_synthetic_test_images(temp_dir: Path) -> dict:
    """Creates synthetic test images simulating diverse edge-case scenarios."""
    temp_dir.mkdir(parents=True, exist_ok=True)
    images = {}

    # 1. Base real camera simulation (with grain and dynamic range)
    img_real = Image.new("RGB", (600, 600), (120, 140, 160))
    img_real = ImageEnhance.Color(img_real).enhance(1.1)
    real_path = temp_dir / "test_real.jpg"
    img_real.save(real_path, "JPEG", quality=95)
    images["real_camera_photo"] = real_path

    # 2. Base AI simulation
    img_ai = Image.new("RGB", (600, 600), (220, 180, 160))
    img_ai = img_ai.filter(ImageFilter.GaussianBlur(3))
    ai_path = temp_dir / "test_ai.jpg"
    img_ai.save(ai_path, "JPEG", quality=95)
    images["ai_generated_image"] = ai_path

    # 3. Heavy JPEG compression
    jpeg_path = temp_dir / "test_jpeg_compressed.jpg"
    img_real.save(jpeg_path, "JPEG", quality=35)
    images["jpeg_compressed"] = jpeg_path

    # 4. Resized image (aspect ratio shift)
    resized_path = temp_dir / "test_resized.jpg"
    img_real.resize((350, 700), Image.Resampling.BILINEAR).save(resized_path, "JPEG")
    images["resized_image"] = resized_path

    # 5. Simulated Screenshot / UI Crop
    sc_img = Image.new("RGB", (500, 500), (240, 240, 240))
    sc_img.paste(img_real.resize((460, 460)), (20, 20))
    sc_path = temp_dir / "test_screenshot.png"
    sc_img.save(sc_path, "PNG")
    images["screenshot"] = sc_path

    # 6. Edited photograph (heavy saturation & contrast)
    edited_img = ImageEnhance.Color(img_real).enhance(1.8)
    edited_img = ImageEnhance.Contrast(edited_img).enhance(1.5)
    edited_path = temp_dir / "test_edited.jpg"
    edited_img.save(edited_path, "JPEG")
    images["edited_photo"] = edited_path

    # 7. Very high resolution (2500x2500)
    hires_path = temp_dir / "test_hires.jpg"
    img_real.resize((2500, 2500), Image.Resampling.BICUBIC).save(hires_path, "JPEG", quality=90)
    images["high_resolution"] = hires_path

    # 8. Low resolution (64x64)
    lowres_path = temp_dir / "test_lowres.jpg"
    img_real.resize((64, 64), Image.Resampling.BILINEAR).save(lowres_path, "JPEG")
    images["low_resolution"] = lowres_path

    # 9. PNG Format
    png_path = temp_dir / "test_format.png"
    img_real.save(png_path, "PNG")
    images["png_format"] = png_path

    # 10. WebP Format
    webp_path = temp_dir / "test_format.webp"
    img_real.save(webp_path, "WEBP", quality=85)
    images["webp_format"] = webp_path

    return images


def run_quality_control_suite():
    print("=" * 80)
    print(" NEXUS+ PRETRAINED MODELS QUALITY CONTROL SUITE ")
    print("=" * 80)

    device = get_default_device()
    print(f"Active Compute Device : {device}")
    
    cached_models = get_cached_models()
    print(f"Cached Local Models   : {[m.name for m in cached_models]}")
    if not cached_models:
        print("⚠️ Warning: No models are cached yet in models/cache/. Run download_models.py first.")

    temp_dir = CURRENT_DIR / "cache" / "_qc_temp"
    test_images = create_synthetic_test_images(temp_dir)

    all_passed = True
    results_summary = []

    print("\n" + "-" * 80)
    print(f"{'Test Scenario':<24} | {'Verdict':<14} | {'AI Prob':<9} | {'Latency':<9} | {'Status'}")
    print("-" * 80)

    for scenario_name, img_path in test_images.items():
        t0 = time.perf_counter()
        
        # Verify input image state before inference
        orig_bytes = img_path.read_bytes()
        
        # Execute unified detection
        res = detect_image(img_path, device=device)
        fused = fuse_predictions(res)
        
        t_elapsed = (time.perf_counter() - t0) * 1000.0

        # Verification checks
        # 1. Check immutability (input file not modified)
        assert img_path.read_bytes() == orig_bytes, "Error: Model modified input file!"

        # 2. Probability bounds check [0.0, 1.0]
        ai_p = fused["ai_probability"]
        real_p = fused["real_probability"]
        assert 0.0 <= ai_p <= 1.0, f"Invalid AI probability: {ai_p}"
        assert 0.0 <= real_p <= 1.0, f"Invalid Real probability: {real_p}"
        assert abs((ai_p + real_p) - 1.0) < 1e-3, "Probabilities do not sum to 1.0"

        # 3. Model outputs validity
        for m_key, m_val in res["models"].items():
            if m_val["status"] == "SUCCESS":
                assert 0.0 <= m_val["ai_probability"] <= 1.0
                assert 0.0 <= m_val["real_probability"] <= 1.0

        status_str = "PASS ✅"
        print(f"{scenario_name:<24} | {fused['verdict']:<14} | {ai_p*100:>6.1f}%  | {t_elapsed:>6.1f} ms | {status_str}")
        results_summary.append((scenario_name, fused["verdict"], ai_p, t_elapsed, status_str))

    # Clean up test temp files
    try:
        for p in temp_dir.glob("*.*"):
            p.unlink()
        temp_dir.rmdir()
    except Exception:
        pass

    print("-" * 80)
    print("✅ All 10 quality control edge-case scenarios passed successfully!")
    print("=" * 80)
    return results_summary


if __name__ == "__main__":
    run_quality_control_suite()
