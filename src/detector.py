from transformers import pipeline
import numpy as np
import cv2
import torch
import open_clip

# ─────────────────────────────────────────────
# LOAD MODELS
# ─────────────────────────────────────────────
MODELS = {
    "sdxl": "Organika/sdxl-detector",
    "general": "umm-maybe/AI-image-detector",
}

pipes = {}

def load_pipelines():
    global pipes
    if pipes:
        return pipes

    for key, model_name in MODELS.items():
        try:
            pipes[key] = pipeline("image-classification", model=model_name)
        except:
            pass

    return pipes


# ─────────────────────────────────────────────
# CLIP
# ─────────────────────────────────────────────
clip_model, _, clip_preprocess = open_clip.create_model_and_transforms(
    "ViT-B-32", pretrained="openai"
)
tokenizer = open_clip.get_tokenizer("ViT-B-32")


def analyze_clip(image):
    img = clip_preprocess(image).unsqueeze(0)

    text = tokenizer([
        "real human face",
        "AI generated face"
    ])

    with torch.no_grad():
        image_features = clip_model.encode_image(img)
        text_features = clip_model.encode_text(text)
        probs = (image_features @ text_features.T).softmax(dim=-1)

    return probs[0][1].item()


# ─────────────────────────────────────────────
# MODEL ENSEMBLE
# ─────────────────────────────────────────────
def analyze_models(image):
    pipes = load_pipelines()
    probs = []

    for pipe in pipes.values():
        try:
            out = pipe(image)[0]
            label = out["label"].lower()
            score = float(out["score"])

            if "ai" in label or "fake" in label:
                probs.append(score)
            else:
                probs.append(1 - score)
        except:
            continue

    return np.mean(probs) if probs else 0


# ─────────────────────────────────────────────
# ARTIFACT DETECTION
# ─────────────────────────────────────────────
def analyze_artifacts(image):
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    noise = np.std(gray)

    score = 0

    if blur < 30:
        score += 25
    elif blur > 150:
        score += 15

    if noise < 20:
        score += 25

    if noise < 10:
        score += 20

    return min(score, 100)


# ─────────────────────────────────────────────
# SYMMETRY
# ─────────────────────────────────────────────
def analyze_symmetry(image):
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    h, w = gray.shape
    left = gray[:, :w//2]
    right = cv2.flip(gray[:, w//2:], 1)

    diff = np.mean(np.abs(left - right))

    if diff < 5:
        return 30
    elif diff < 10:
        return 15
    return 0


# ─────────────────────────────────────────────
# 🔥 FREQUENCY ANALYSIS (V4)
# ─────────────────────────────────────────────
def analyze_frequency(image):
    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)

    magnitude = np.log(np.abs(fshift) + 1)

    h, w = magnitude.shape
    center = magnitude[h//4:3*h//4, w//4:3*w//4]

    outer = magnitude.copy()
    outer[h//4:3*h//4, w//4:3*w//4] = 0

    center_energy = np.mean(center)
    outer_energy = np.mean(outer)

    ratio = outer_energy / (center_energy + 1e-5)

    if ratio < 0.8:
        return 30
    elif ratio < 1.0:
        return 15
    return 0


# ─────────────────────────────────────────────
# METADATA
# ─────────────────────────────────────────────
def analyze_metadata(username, bio, followers, following, posts, age):
    score = 0
    flags = []

    if followers < 10 and age < 30:
        score += 20
        flags.append("Low followers + new account")

    if posts == 0:
        score += 15
        flags.append("No posts")

    if len(username) > 12 and any(char.isdigit() for char in username):
        score += 10
        flags.append("Suspicious username")

    return score, flags


# ─────────────────────────────────────────────
# FINAL ANALYSIS (V4)
# ─────────────────────────────────────────────
def full_profile_analysis(
    image_source,
    username="",
    bio="",
    followers=0,
    posts=0,
    following=0,
    account_age_days=0
):
    model_score = analyze_models(image_source)
    clip_score = analyze_clip(image_source)
    artifact_score = analyze_artifacts(image_source)
    symmetry_score = analyze_symmetry(image_source)
    frequency_score = analyze_frequency(image_source)

    meta_score, flags = analyze_metadata(
        username, bio, followers, following, posts, account_age_days
    )

    # 🔥 FINAL SCORE (AGGRESSIVE + SMART)
    base_suspicion = 25

    final_score = (
        base_suspicion +
        model_score * 25 +
        clip_score * 20 +
        artifact_score * 0.3 +
        symmetry_score * 0.2 +
        frequency_score * 0.4 +
        meta_score * 0.2
    )

    is_ai = final_score > 40

    if final_score > 65:
        verdict = "🚨 Likely AI"
    elif final_score > 40:
        verdict = "⚠️ Suspicious"
    else:
        verdict = "✅ Likely Real"

    return {
        "overall_suspicion_score": final_score,
        "overall_verdict": verdict,
        "image_analysis": {
            "ai_probability": final_score / 100,
            "is_ai_generated": is_ai,
            "confidence_level": "high" if final_score > 65 else "medium" if final_score > 40 else "low",
            "individual_results": {}
        },
        "metadata_analysis": {
            "metadata_suspicion_score": meta_score,
            "verdict": "Moderate" if meta_score > 20 else "Low",
            "red_flags": flags
        },
        "clip_score": clip_score * 100,
        "artifact_score": artifact_score,
        "symmetry_score": symmetry_score,
        "frequency_score": frequency_score
    }