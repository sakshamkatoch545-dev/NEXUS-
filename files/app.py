"""
app.py — Streamlit frontend for Fake AI Profile Detector
Day 2: Added sidebar model selector, Fine-Tune button (background thread),
       live st.progress + st.status during training, auto-reload after completion.
"""

import streamlit as st
import sys
import os
import json
import time
import threading
import subprocess

# Make sure project root is importable
sys.path.append(os.path.dirname(__file__))

from detector import (
    AdvancedAIImageDetector,
    detect_fake_profile,
    FINE_TUNED_DIR,
    PRETRAINED_MODEL,
)

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

FINE_TUNED_EVAL_JSON = os.path.join(FINE_TUNED_DIR, "eval_results.json")
FINE_TUNED_CURVES    = os.path.join(FINE_TUNED_DIR, "training_curves.png")
TRAINING_LOG_FILE    = os.path.join(FINE_TUNED_DIR, "training_log.txt")


# ──────────────────────────────────────────────
# Cached detector — rebuilds when model_name changes
# ──────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading model …")
def get_detector(model_name: str) -> AdvancedAIImageDetector:
    """Cache the detector per model_name so switching models reloads cleanly."""
    return AdvancedAIImageDetector(model_name=model_name)


# ──────────────────────────────────────────────
# Helper: read fine-tuned eval results (if present)
# ──────────────────────────────────────────────

def _load_fine_tuned_eval() -> dict | None:
    if os.path.exists(FINE_TUNED_EVAL_JSON):
        with open(FINE_TUNED_EVAL_JSON) as f:
            return json.load(f)
    return None


# ──────────────────────────────────────────────
# Helper: is fine-tuned model available?
# ──────────────────────────────────────────────

def _fine_tuned_available() -> bool:
    # HF saves config.json + pytorch_model.bin (or model.safetensors)
    config_ok = os.path.exists(os.path.join(FINE_TUNED_DIR, "config.json"))
    model_ok  = (
        os.path.exists(os.path.join(FINE_TUNED_DIR, "pytorch_model.bin")) or
        os.path.exists(os.path.join(FINE_TUNED_DIR, "model.safetensors"))
    )
    return config_ok and model_ok


# ──────────────────────────────────────────────
# Background training thread
# ──────────────────────────────────────────────

def _run_training_background(epochs: int, batch_size: int) -> None:
    """
    Runs train.py in a subprocess so the Streamlit process stays alive.
    Writes stdout+stderr to TRAINING_LOG_FILE for the UI to tail.
    Sets st.session_state flags when done.
    """
    os.makedirs(FINE_TUNED_DIR, exist_ok=True)

    cmd = [
        sys.executable, "train.py",
        "--epochs",     str(epochs),
        "--batch_size", str(batch_size),
        "--output_dir", FINE_TUNED_DIR,
    ]

    with open(TRAINING_LOG_FILE, "w") as log_f:
        proc = subprocess.Popen(
            cmd,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            text=True,
        )
        proc.wait()

    # Signal completion back to Streamlit via session_state
    # (Streamlit re-runs on next interaction, which will pick this up)
    if proc.returncode == 0:
        st.session_state["training_status"]  = "done"
        st.session_state["training_error"]   = None
    else:
        st.session_state["training_status"]  = "error"
        st.session_state["training_error"]   = (
            f"train.py exited with code {proc.returncode}. "
            f"Check {TRAINING_LOG_FILE} for details."
        )


# ──────────────────────────────────────────────
# Session state defaults
# ──────────────────────────────────────────────

def _init_session_state():
    defaults = {
        "training_status":  "idle",    # idle | running | done | error
        "training_error":   None,
        "training_thread":  None,
        "selected_model":   "Pre-trained",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Fake AI Profile Detector",
    page_icon="🕵️",
    layout="wide",
)

_init_session_state()


# ──────────────────────────────────────────────
# SIDEBAR — Model selection + fine-tuning
# ──────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Model Settings")
    st.markdown("---")

    # ── Model selector ─────────────────────────
    fine_tuned_ready = _fine_tuned_available()
    model_options    = ["Pre-trained"]
    if fine_tuned_ready:
        model_options.append("Fine-tuned Model")

    selected_label = st.radio(
        "Active model",
        options=model_options,
        index=model_options.index(st.session_state["selected_model"])
              if st.session_state["selected_model"] in model_options else 0,
        key="model_radio",
    )
    st.session_state["selected_model"] = selected_label

    # Map UI label → model_name string passed to AdvancedAIImageDetector
    if selected_label == "Fine-tuned Model":
        active_model_name = FINE_TUNED_DIR
    else:
        active_model_name = PRETRAINED_MODEL

    # ── Current model info ─────────────────────
    st.markdown("**Current model**")
    st.code(
        "umm-maybe/AI-image-detector"
        if active_model_name == PRETRAINED_MODEL
        else "google/vit-base-patch16-224\n(fine-tuned locally)",
        language="text",
    )

    # ── Fine-tuned eval accuracy ───────────────
    if fine_tuned_ready:
        eval_data = _load_fine_tuned_eval()
        if eval_data:
            acc = eval_data.get("eval_accuracy", 0.0)
            st.metric(
                label="Fine-tuned val accuracy",
                value=f"{acc * 100:.1f}%",
                delta=f"{'✅ ≥85%' if acc >= 0.85 else '⚠️ <85% target'}",
            )

    st.markdown("---")

    # ── Fine-tune section ──────────────────────
    st.markdown("**🎯 Fine-Tune on Your Data**")
    st.caption(
        "Trains `google/vit-base-patch16-224` on images in "
        "`test_images/ai/` and `test_images/real/`."
    )

    ft_epochs     = st.slider("Epochs",     min_value=1, max_value=10, value=5)
    ft_batch_size = st.select_slider("Batch size", options=[4, 8, 16, 32], value=8)

    training_status = st.session_state["training_status"]

    fine_tune_btn = st.button(
        "🚀 Fine-Tune Model",
        use_container_width=True,
        type="primary",
        disabled=(training_status == "running"),
    )

    if fine_tune_btn:
        # Clear any previous results
        st.session_state["training_status"] = "running"
        st.session_state["training_error"]  = None

        # Invalidate cached fine-tuned detector so it reloads after training
        get_detector.clear()

        thread = threading.Thread(
            target=_run_training_background,
            args=(ft_epochs, ft_batch_size),
            daemon=True,
        )
        thread.start()
        st.session_state["training_thread"] = thread
        st.rerun()

    # ── Training status display ────────────────
    if training_status == "running":
        st.info("⏳ Training in progress …", icon="🔄")

        # Tail the log file to give the user live feedback
        if os.path.exists(TRAINING_LOG_FILE):
            with open(TRAINING_LOG_FILE) as lf:
                lines = lf.readlines()
            recent = "".join(lines[-20:]) if lines else "(waiting for output …)"
            with st.expander("📋 Training log (last 20 lines)", expanded=True):
                st.code(recent, language="text")

        # Auto-refresh every 5 s while training runs
        time.sleep(5)
        st.rerun()

    elif training_status == "done":
        st.success("✅ Training complete! Switch to **Fine-tuned Model** above.")

        # Show curves if available
        if os.path.exists(FINE_TUNED_CURVES):
            with st.expander("📈 Training curves", expanded=False):
                st.image(FINE_TUNED_CURVES)

        # Auto-reload detector with fine-tuned weights
        get_detector.clear()

    elif training_status == "error":
        st.error(f"❌ Training failed:\n{st.session_state['training_error']}")
        if os.path.exists(TRAINING_LOG_FILE):
            with open(TRAINING_LOG_FILE) as lf:
                lines = lf.readlines()
            with st.expander("📋 Full training log"):
                st.code("".join(lines), language="text")

    st.markdown("---")
    st.caption("🕵️ Fake AI Profile Detector · Day 2")


# ──────────────────────────────────────────────
# Load active detector (cached per model_name)
# ──────────────────────────────────────────────

detector = get_detector(active_model_name)


# ──────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────

st.title("🕵️ Fake AI Profile Detector")
st.caption(
    "Analyze a social media profile picture and metadata to detect fake or AI-generated accounts."
)

# Model badge
badge_color = "🟢" if active_model_name == PRETRAINED_MODEL else "🔵"
st.markdown(
    f"{badge_color} **Active model:** `{detector.display_name}`"
)
st.divider()


# ──────────────────────────────────────────────
# Layout: two columns
# ──────────────────────────────────────────────

left_col, right_col = st.columns([1, 1], gap="large")


# ──────────────────────────────────────────────
# LEFT COLUMN — Inputs
# ──────────────────────────────────────────────

with left_col:
    st.subheader("📥 Profile Input")

    # --- Profile picture ---
    st.markdown("**Profile Picture**")
    input_mode = st.radio(
        "Choose input method:",
        ["Upload an image", "Paste image URL"],
        horizontal=True,
    )

    image_path_or_url = None
    uploaded_file     = None

    if input_mode == "Upload an image":
        uploaded_file = st.file_uploader(
            "Upload profile picture",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
        if uploaded_file:
            temp_path = os.path.join("data", "sample_images", "_temp_upload.jpg")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())
            image_path_or_url = temp_path
            st.image(temp_path, caption="Uploaded profile picture", width="stretch")

    else:
        url_input = st.text_input(
            "Image URL",
            placeholder="https://example.com/profile.jpg",
            label_visibility="collapsed",
        )
        if url_input.strip():
            image_path_or_url = url_input.strip()
            st.image(image_path_or_url, caption="Profile picture from URL", width="stretch")

    st.markdown("---")

    # --- Metadata form ---
    st.markdown("**Profile Metadata**")

    username = st.text_input("Username", placeholder="e.g. john_doe_92837")
    bio      = st.text_area("Bio / Description", placeholder="e.g. Travel lover | NYC", height=80)

    col1, col2 = st.columns(2)
    with col1:
        followers = st.number_input("Followers",    min_value=0, value=0, step=1)
        posts     = st.number_input("Posts",        min_value=0, value=0, step=1)
    with col2:
        following         = st.number_input("Following",         min_value=0, value=0, step=1)
        account_age_days  = st.number_input("Account Age (days)", min_value=0, value=0, step=1)

    st.markdown("---")

    # --- Analyze button ---
    analyze_clicked = st.button(
        "🔍 Analyze Profile",
        use_container_width=True,
        type="primary",
    )


# ──────────────────────────────────────────────
# RIGHT COLUMN — Results
# ──────────────────────────────────────────────

with right_col:
    st.subheader("📊 Detection Results")

    if not analyze_clicked:
        st.info(
            "Fill in the profile details on the left and click **Analyze Profile** to see results.",
            icon="👈",
        )

    else:
        # Validate inputs
        if not image_path_or_url:
            st.error("⚠️ Please provide a profile picture (upload or URL) before analyzing.")
        elif not username.strip():
            st.error("⚠️ Please enter a username before analyzing.")
        else:
            with st.spinner("Analyzing profile …"):
                metadata = {
                    "username":        username,
                    "bio":             bio,
                    "followers":       int(followers),
                    "following":       int(following),
                    "posts":           int(posts),
                    "account_age_days": int(account_age_days),
                }

                try:
                    result = detect_fake_profile(
                        image_path_or_url,
                        metadata,
                        detector=detector,          # pass cached detector
                    )

                    # ── Verdict banner ──────────────────────────────
                    verdict = result["verdict"]
                    label   = result["verdict_label"]
                    score   = result["combined_score"]

                    if verdict == "FAKE":
                        st.error(f"## {label}")
                    elif verdict == "SUSPICIOUS":
                        st.warning(f"## {label}")
                    else:
                        st.success(f"## {label}")

                    # ── Combined score bar ──────────────────────────
                    st.markdown("**Overall Suspicion Score**")
                    st.progress(score, text=f"{score * 100:.1f}% suspicious")
                    st.markdown("---")

                    # ── Image analysis ──────────────────────────────
                    st.markdown("### 📸 Image Analysis")
                    img_data   = result["image_analysis"]
                    img_conf   = img_data["confidence"]
                    face_found = img_data["face_detected"]
                    model_used = img_data["model_used"]

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric(
                            label="AI-Generated?",
                            value="Yes 🤖" if img_data["is_ai_generated"] else "No ✅",
                        )
                    with col_b:
                        st.metric(
                            label="Image Suspicion",
                            value=f"{img_conf * 100:.1f}%",
                        )
                    with col_c:
                        st.metric(
                            label="Face Detected",
                            value="Yes 👤" if face_found else "No",
                            help="If a face is found, score = 70% full-image + 30% face-crop.",
                        )

                    st.progress(img_conf, text=f"Image confidence: {img_conf * 100:.1f}%")
                    st.caption(f"Model: {model_used}")
                    st.markdown("---")

                    # ── Metadata analysis ───────────────────────────
                    st.markdown("### 📋 Metadata Analysis")
                    meta_data  = result["metadata_analysis"]
                    meta_score = meta_data["fake_score"]
                    red_flags  = meta_data["red_flags"]

                    st.metric(
                        label="Metadata Suspicion Score",
                        value=f"{meta_score * 100:.1f}%",
                    )
                    st.progress(meta_score, text=f"Metadata score: {meta_score * 100:.1f}%")

                    if red_flags:
                        st.markdown("**🚩 Red Flags Detected:**")
                        for flag in red_flags:
                            st.markdown(f"- {flag}")
                    else:
                        st.success("No metadata red flags detected.")

                except Exception as exc:
                    st.error(f"Detection failed: {exc}")
                    st.caption(
                        "Make sure the image path/URL is valid and "
                        "the detector module is correctly set up."
                    )


# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────

st.divider()
st.caption("🕵️ Fake AI Profile Detector · Day 2 · Built with Streamlit")
