"""
detector.py — Core detection logic for Fake AI Profile Detector
Day 2: Refactored into AdvancedAIImageDetector class.
       Added MediaPipe face detection + 70/30 full/face score blending.
       Optional model_name param supports both pre-trained and fine-tuned ViT.
"""

import os
import io
import re
import requests
import numpy as np
from PIL import Image


# ──────────────────────────────────────────────
# SECTION 1: Image Loading
# ──────────────────────────────────────────────

def _load_image(image_path_or_url: str) -> Image.Image:
    """Load a PIL image from a local path or a URL."""
    if image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://"):
        response = requests.get(image_path_or_url, timeout=10)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGB")
    else:
        if not os.path.exists(image_path_or_url):
            raise FileNotFoundError(f"Image not found: {image_path_or_url}")
        return Image.open(image_path_or_url).convert("RGB")


# ──────────────────────────────────────────────
# SECTION 2: AdvancedAIImageDetector class
# ──────────────────────────────────────────────

FINE_TUNED_DIR    = "./fine_tuned_vit"
FINE_TUNED_LABELS = {"artificial", "ai", "fake", "generated"}   # any of these → AI
PRETRAINED_MODEL  = "umm-maybe/AI-image-detector"


class AdvancedAIImageDetector:
    """
    Detects whether an image is AI-generated using:
      1. A HuggingFace image-classification model (pre-trained or fine-tuned ViT).
      2. MediaPipe face detection — if a face is found, a cropped face score is
         blended with the full-image score at a 70 / 30 ratio (full / face).

    Parameters
    ----------
    model_name : str
        HuggingFace model ID  **or**  a local directory path.
        Defaults to the pre-trained "umm-maybe/AI-image-detector".
        Pass FINE_TUNED_DIR (or "./fine_tuned_vit") to use the fine-tuned ViT.
    """

    # ── Construction ──────────────────────────────────────────────────────────

    def __init__(self, model_name: str = PRETRAINED_MODEL):
        self.model_name = model_name
        self._pipeline  = None          # lazy-loaded HF pipeline
        self._mp_face   = None          # lazy-loaded MediaPipe detector
        self._is_fine_tuned = os.path.isdir(model_name)   # local dir → fine-tuned

    # ── Lazy loaders ──────────────────────────────────────────────────────────

    def _get_pipeline(self):
        """Lazy-load the HuggingFace image-classification pipeline."""
        if self._pipeline is None:
            from transformers import pipeline as hf_pipeline
            print(f"[detector] Loading model: {self.model_name} …")
            self._pipeline = hf_pipeline(
                "image-classification",
                model=self.model_name,
            )
            print("[detector] Model ready.")
        return self._pipeline

    def _get_face_detector(self):
        """Lazy-load MediaPipe Face Detection (short-range, model 0)."""
        if self._mp_face is None:
            try:
                import mediapipe as mp
                self._mp_face = mp.solutions.face_detection.FaceDetection(
                    model_selection=0,      # 0 = short-range (≤2 m), good for profile pics
                    min_detection_confidence=0.5,
                )
                print("[detector] MediaPipe face detector ready.")
            except ImportError:
                print("[detector] MediaPipe not installed — face crop disabled.")
                self._mp_face = None
        return self._mp_face

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _classify(self, img: Image.Image) -> float:
        """
        Run the HF pipeline on a PIL image.
        Returns the AI/artificial confidence as a float in [0, 1].
        """
        pipe    = self._get_pipeline()
        results = pipe(img)

        if self._is_fine_tuned:
            # Fine-tuned ViT: label 0 = artificial, label 1 = real
            # id2label stored in config: {"0": "artificial", "1": "real"}
            scores = {}
            for r in results:
                raw_label = str(r["label"]).lower()
                # Handle both "LABEL_0" style and "artificial" style
                if raw_label in ("label_0", "0", "artificial", "ai", "fake", "generated"):
                    scores["artificial"] = r["score"]
                elif raw_label in ("label_1", "1", "real", "human", "genuine"):
                    scores["real"] = r["score"]
            # If model outputs softmax, artificial + real ≈ 1.0
            # Fallback: if neither key found, treat top label as artificial
            if "artificial" not in scores and results:
                scores["artificial"] = results[0]["score"]
        else:
            # Pre-trained umm-maybe model: labels are "artificial" / "real"
            scores = {r["label"].lower(): r["score"] for r in results}

        return float(scores.get("artificial", 0.0))

    def _detect_and_crop_face(self, img: Image.Image) -> Image.Image | None:
        """
        Use MediaPipe to find the largest face in *img*.
        Returns a cropped PIL Image or None if no face found / MediaPipe unavailable.
        """
        face_detector = self._get_face_detector()
        if face_detector is None:
            return None

        import mediapipe as mp

        img_np  = np.array(img)                     # H × W × 3, uint8 RGB
        h, w    = img_np.shape[:2]

        results = face_detector.process(img_np)

        if not results.detections:
            return None

        # Pick detection with highest confidence
        best = max(results.detections, key=lambda d: d.score[0])
        bbox = best.location_data.relative_bounding_box

        # Convert relative → absolute, with 20 % padding
        pad  = 0.20
        x1   = max(0, int((bbox.xmin - pad * bbox.width)  * w))
        y1   = max(0, int((bbox.ymin - pad * bbox.height) * h))
        x2   = min(w, int((bbox.xmin + (1 + pad) * bbox.width)  * w))
        y2   = min(h, int((bbox.ymin + (1 + pad) * bbox.height) * h))

        if x2 <= x1 or y2 <= y1:
            return None

        return img.crop((x1, y1, x2, y2))

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, image_path_or_url: str) -> tuple:
        """
        Detect whether the image at *image_path_or_url* is AI-generated.

        Scoring
        -------
        - Full-image score is always computed.
        - If a face is detected, a face-crop score is computed too and
          blended: final = 0.70 × full_score + 0.30 × face_score.

        Returns
        -------
        (is_ai: bool, confidence: float, face_found: bool)
        """
        try:
            img = _load_image(image_path_or_url)
        except Exception as exc:
            print(f"[detector] Could not load image: {exc}")
            return False, 0.0, False

        try:
            # 1. Full-image score
            full_score = self._classify(img)

            # 2. Face-crop score (optional)
            face_img   = self._detect_and_crop_face(img)
            face_found = face_img is not None

            if face_found:
                face_score = self._classify(face_img)
                confidence = round(0.70 * full_score + 0.30 * face_score, 4)
            else:
                confidence = round(full_score, 4)

            is_ai = confidence >= 0.5
            return is_ai, confidence, face_found

        except Exception as exc:
            print(f"[detector] Inference failed: {exc}")
            return False, 0.0, False

    @property
    def display_name(self) -> str:
        """Human-readable model name for the UI."""
        if self._is_fine_tuned:
            return "Fine-tuned ViT (google/vit-base-patch16-224)"
        return self.model_name


# ──────────────────────────────────────────────
# SECTION 3: Metadata Analysis  (unchanged from Day 1)
# ──────────────────────────────────────────────

def analyze_basic_metadata(
    username: str,
    bio: str,
    followers: int,
    following: int,
    posts: int,
    account_age_days: int,
) -> tuple:
    """
    Score how suspicious a profile's metadata looks.
    Returns (fake_score: float, reasons: list)
    """
    reasons = []
    signals = []

    if re.search(r'\d{4,}', username):
        reasons.append("Username contains a long numeric sequence (common in auto-generated accounts).")
        signals.append(0.6)

    if len(username) > 20:
        reasons.append("Username is unusually long.")
        signals.append(0.3)

    if not bio or len(bio.strip()) < 5:
        reasons.append("Bio is empty or very short.")
        signals.append(0.5)

    if following > 0 and followers / (following + 1) < 0.1:
        reasons.append("Very low follower-to-following ratio.")
        signals.append(0.7)

    if followers > 10_000 and posts < 10:
        reasons.append("High follower count but very few posts.")
        signals.append(0.8)

    if account_age_days > 0:
        posts_per_day = posts / account_age_days
        if posts_per_day > 20:
            reasons.append(f"Unusually high post frequency ({posts_per_day:.1f} posts/day).")
            signals.append(0.7)
        if posts_per_day == 0 and account_age_days > 30:
            reasons.append("Account is over 30 days old but has zero posts.")
            signals.append(0.6)

    if account_age_days < 7 and followers > 500:
        reasons.append("Very new account with a suspiciously high follower count.")
        signals.append(0.9)

    fake_score = round(min(1.0, sum(signals) / len(signals) * 1.2), 4) if signals else 0.0

    return fake_score, reasons


# ──────────────────────────────────────────────
# SECTION 4: Combined Detection  (public entry point)
# ──────────────────────────────────────────────

def detect_fake_profile(
    image_path_or_url: str,
    metadata_dict: dict,
    detector: AdvancedAIImageDetector | None = None,
) -> dict:
    """
    Master function: combines image + metadata analysis.

    Parameters
    ----------
    image_path_or_url : str
        Local file path or HTTP(S) URL.
    metadata_dict : dict
        Keys: username, bio, followers, following, posts, account_age_days.
    detector : AdvancedAIImageDetector | None
        Pass a pre-loaded detector to avoid reloading the model on every call.
        If None, a default pre-trained detector is created.

    Returns a result dictionary with verdict and full breakdown.
    """
    if detector is None:
        detector = AdvancedAIImageDetector()

    is_ai_image, image_confidence, face_found = detector.detect(image_path_or_url)

    fake_score, reasons = analyze_basic_metadata(
        username=metadata_dict.get("username", ""),
        bio=metadata_dict.get("bio", ""),
        followers=metadata_dict.get("followers", 0),
        following=metadata_dict.get("following", 0),
        posts=metadata_dict.get("posts", 0),
        account_age_days=metadata_dict.get("account_age_days", 0),
    )

    # 50 / 50 weight — image model is now reliable
    combined_score = round(fake_score * 0.5 + image_confidence * 0.5, 4)

    if combined_score >= 0.6:
        verdict       = "FAKE"
        verdict_label = "⚠️ Likely Fake / AI-Generated"
    elif combined_score >= 0.35:
        verdict       = "SUSPICIOUS"
        verdict_label = "🔍 Suspicious — Needs Review"
    else:
        verdict       = "REAL"
        verdict_label = "✅ Likely Real"

    return {
        "verdict":       verdict,
        "verdict_label": verdict_label,
        "combined_score": combined_score,
        "image_analysis": {
            "is_ai_generated": is_ai_image,
            "confidence":      image_confidence,
            "face_detected":   face_found,
            "model_used":      detector.display_name,
        },
        "metadata_analysis": {
            "fake_score": fake_score,
            "red_flags":  reasons,
        },
    }
