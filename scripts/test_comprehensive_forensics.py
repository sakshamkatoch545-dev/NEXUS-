"""
test_comprehensive_forensics.py — Backend Validation & Test Suite
==================================================================
Runs comprehensive image forensics across all 12 required test scenarios:
1. genuine camera photograph
2. fully AI-generated image
3. AI-generated portrait
4. AI-generated landscape
5. real photo with AI background replacement
6. real photo with AI object replacement
7. AI inpainting
8. normal Photoshop/color correction
9. JPEG-compressed real photograph
10. screenshot
11. resized image
12. ambiguous image

Records verdict, confidence, probabilities, manipulation, regions, explanations, models, and latency.
"""

import os
import sys
import time
import json
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.detector import full_image_analysis


def generate_synthetic_evaluation_dataset(temp_dir: Path) -> dict:
    temp_dir.mkdir(parents=True, exist_ok=True)
    images = {}

    # 1. Genuine camera photograph (realistic dynamic range, natural noise texture)
    base_real = Image.new("RGB", (640, 480), (130, 150, 170))
    # Add subtle organic noise
    draw = ImageDraw.Draw(base_real)
    for i in range(0, 640, 20):
        draw.line([(i, 0), (i, 480)], fill=(128 + (i % 7), 148, 168), width=2)
    real_path = temp_dir / "01_genuine_camera_photo.jpg"
    base_real.save(real_path, "JPEG", quality=95)
    images["1. Genuine Camera Photograph"] = real_path

    # 2. Fully AI-generated image (extreme smooth textures, low high-frequency residuals)
    base_ai = Image.new("RGB", (640, 480), (220, 180, 160))
    base_ai = base_ai.filter(ImageFilter.GaussianBlur(3))
    ai_path = temp_dir / "02_fully_ai_generated.jpg"
    base_ai.save(ai_path, "JPEG", quality=95)
    images["2. Fully AI-Generated Image"] = ai_path

    # 3. AI-generated portrait (high facial saturation, smooth gradients)
    ai_portrait = Image.new("RGB", (512, 512), (235, 170, 140))
    ai_portrait = ai_portrait.filter(ImageFilter.GaussianBlur(2))
    ai_portrait = ImageEnhance.Color(ai_portrait).enhance(1.4)
    ai_portrait_path = temp_dir / "03_ai_generated_portrait.jpg"
    ai_portrait.save(ai_portrait_path, "JPEG", quality=95)
    images["3. AI-Generated Portrait"] = ai_portrait_path

    # 4. AI-generated landscape (synthetic color gamut)
    ai_landscape = Image.new("RGB", (768, 512), (100, 180, 220))
    ai_landscape = ai_landscape.filter(ImageFilter.GaussianBlur(2.5))
    ai_landscape_path = temp_dir / "04_ai_generated_landscape.jpg"
    ai_landscape.save(ai_landscape_path, "JPEG", quality=95)
    images["4. AI-Generated Landscape"] = ai_landscape_path

    # 5. Real photo with AI background replacement (isolated background patch anomaly)
    ai_bg = base_real.copy()
    bg_patch = Image.new("RGB", (640, 240), (230, 190, 170)).filter(ImageFilter.GaussianBlur(4))
    ai_bg.paste(bg_patch, (0, 0))
    ai_bg_path = temp_dir / "05_real_with_ai_background.jpg"
    ai_bg.save(ai_bg_path, "JPEG", quality=95)
    images["5. Real Photo with AI Background Replacement"] = ai_bg_path

    # 6. Real photo with AI object replacement (localized bounding anomaly)
    ai_obj = base_real.copy()
    obj_patch = Image.new("RGB", (160, 160), (240, 120, 100)).filter(ImageFilter.GaussianBlur(3))
    ai_obj.paste(obj_patch, (200, 150))
    ai_obj_path = temp_dir / "06_real_with_ai_object.jpg"
    ai_obj.save(ai_obj_path, "JPEG", quality=95)
    images["6. Real Photo with AI Object Replacement"] = ai_obj_path

    # 7. AI inpainting (patch generative fill)
    ai_inpaint = base_real.copy()
    inpaint_patch = Image.new("RGB", (120, 120), (210, 210, 210)).filter(ImageFilter.GaussianBlur(3.5))
    ai_inpaint.paste(inpaint_patch, (300, 200))
    ai_inpaint_path = temp_dir / "07_ai_inpainting.jpg"
    ai_inpaint.save(ai_inpaint_path, "JPEG", quality=95)
    images["7. AI Inpainting / Generative Fill"] = ai_inpaint_path

    # 8. Normal Photoshop / color correction (global tone shift without generative inpainting)
    edited_photo = ImageEnhance.Color(base_real).enhance(1.2)
    edited_photo = ImageEnhance.Contrast(edited_photo).enhance(1.1)
    edited_path = temp_dir / "08_photoshop_color_correction.jpg"
    edited_photo.save(edited_path, "JPEG", quality=95)
    images["8. Normal Photoshop / Color Correction"] = edited_path

    # 9. JPEG-compressed real photograph (quality 40 compression artifacts)
    jpeg_path = temp_dir / "09_jpeg_compressed_photo.jpg"
    base_real.save(jpeg_path, "JPEG", quality=40)
    images["9. JPEG-Compressed Real Photograph"] = jpeg_path

    # 10. Screenshot (UI borders with natural photographic crop)
    sc_img = Image.new("RGB", (600, 500), (245, 245, 245))
    sc_img.paste(base_real.resize((520, 420)), (40, 40))
    sc_path = temp_dir / "10_screenshot.png"
    sc_img.save(sc_path, "PNG")
    images["10. Screenshot / UI Crop"] = sc_path

    # 11. Resized image (altered aspect ratio and interpolation)
    resized_path = temp_dir / "11_resized_image.jpg"
    base_real.resize((320, 640), Image.Resampling.BILINEAR).save(resized_path, "JPEG")
    images["11. Resized Image"] = resized_path

    # 12. Ambiguous image (subtle mixed indicators)
    amb_img = Image.blend(base_real, base_ai, 0.45)
    amb_path = temp_dir / "12_ambiguous_image.jpg"
    amb_img.save(amb_path, "JPEG", quality=85)
    images["12. Ambiguous Image"] = amb_path

    return images


def run_comprehensive_evaluation():
    print("=" * 80)
    print(" NEXUS+ COMPREHENSIVE IMAGE FORENSICS BACKEND EVALUATION ")
    print("=" * 80)

    temp_dir = PROJECT_ROOT / "scratch" / "_eval_cases"
    test_cases = generate_synthetic_evaluation_dataset(temp_dir)

    results = []

    for idx, (title, img_path) in enumerate(test_cases.items(), 1):
        print(f"\n[{idx}/12] Evaluating: {title} ...")
        t0 = time.perf_counter()
        
        img = Image.open(img_path)
        res = full_image_analysis(img)
        t_elapsed = (time.perf_counter() - t0) * 1000.0

        # Extract structured response values
        v = res.get("standard_verdict", res.get("verdict"))
        conf = res.get("confidence", res.get("confidence_score"))
        probs = res.get("probabilities", {})
        manip = res.get("manipulation", {})
        regions = res.get("regions", [])
        expl = res.get("explanation", [])
        models = res.get("models", [])
        analysis = res.get("analysis", {})

        print(f"       Verdict       : {v}")
        print(f"       Confidence    : {conf}%")
        print(f"       Probabilities : Real={probs.get('real', 0)}%, AI-Gen={probs.get('ai_generated', 0)}%, AI-Edit={probs.get('ai_edited', 0)}%")
        print(f"       Manipulation  : Detected={manip.get('detected', False)}, Type={manip.get('type')}, Severity={manip.get('severity', 0.0)}")
        print(f"       Suspicious Reg: {len(regions)} region(s)")
        print(f"       Models Count  : {len(models)} active model(s)")
        print(f"       Latency       : {t_elapsed:.1f} ms")
        print(f"       Explanation   : {expl[0] if expl else 'None'}")

        results.append({
            "test_case": title,
            "verdict": v,
            "confidence": conf,
            "probabilities": probs,
            "manipulation": manip,
            "regions_count": len(regions),
            "latency_ms": round(t_elapsed, 1),
            "explanation": expl,
            "models_count": len(models)
        })

    # Save summary report
    report_path = PROJECT_ROOT / "results" / "comprehensive_forensics_evaluation.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print(f"Evaluation complete! Recorded 12 test reports -> {report_path}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_comprehensive_evaluation()
