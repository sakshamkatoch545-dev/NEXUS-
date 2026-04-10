import streamlit as st
from PIL import Image
import requests
from io import BytesIO
from src.detector import full_profile_analysis

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🕵️ Fake AI Profile Detector",
    page_icon="🕵️",
    layout="wide",
)

st.title("🕵️ Fake AI Profile Detector V2")
st.markdown("Now powered by **CLIP + Ensemble Detection 🔥**")
st.divider()

# ─────────────────────────────────────────────
# INPUT SECTION
# ─────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("📥 Input")

    method = st.radio("Choose input method:", ["Upload", "URL"])

    image = None

    if method == "Upload":
        file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg", "webp"])
        if file:
            image = Image.open(file).convert("RGB")
            st.image(image, use_container_width=True)

    else:
        url = st.text_input("Enter Image URL")
        if url:
            try:
                response = requests.get(url)
                image = Image.open(BytesIO(response.content)).convert("RGB")
                st.image(image, use_container_width=True)
            except:
                st.error("Invalid URL")

    st.subheader("📋 Metadata (Optional)")
    username = st.text_input("Username")
    bio = st.text_area("Bio")
    followers = st.number_input("Followers", 0)
    following = st.number_input("Following", 0)
    posts = st.number_input("Posts", 0)
    age = st.number_input("Account Age (days)", 0)

    analyze = st.button("Analyze 🔍")

# ─────────────────────────────────────────────
# OUTPUT SECTION
# ─────────────────────────────────────────────
with col2:
    st.subheader("📊 Results")

    if analyze:
        if image is None:
            st.warning("Please upload an image")
        else:
            with st.spinner("Analyzing..."):
                result = full_profile_analysis(
                    image_source=image,
                    username=username,
                    bio=bio,
                    followers=followers,
                    following=following,
                    posts=posts,
                    account_age_days=age
                )

            score = result["overall_suspicion_score"]
            verdict = result["overall_verdict"]

            # ── Verdict ──
            st.markdown(f"## {verdict}")
            st.progress(int(score))
            st.write(f"**Score:** {score:.2f} / 100")

            # ── Image Analysis ──
            st.subheader("📸 Image Analysis")

            img = result["image_analysis"]

            st.metric("AI Generated?", "🤖 Yes" if img["is_ai_generated"] else "👤 No")
            st.metric("Confidence", img["confidence_level"].upper())

            # Models
            st.markdown("**Model Breakdown:**")
            for name, r in img["individual_results"].items():
                st.write(f"- {name}: {r['ai_probability']*100:.1f}% AI")

            # ── Extra Scores ──
            st.subheader("🧠 Advanced Signals")
            st.write(f"CLIP Score: {result.get('clip_score', 0):.1f}")
            st.write(f"Artifact Score: {result.get('artifact_score', 0):.1f}")

            # ── Metadata ──
            st.subheader("📋 Metadata Analysis")

            meta = result["metadata_analysis"]

            st.write(f"Score: {meta['metadata_suspicion_score']}")

            # SAFE ACCESS (no crash)
            flags = meta.get("red_flags", [])

            if flags:
                for f in flags:
                    st.warning(f)
            else:
                st.success("No red flags")

    else:
        st.info("Upload image and click Analyze")

st.divider()
st.caption("V2 Detector • CLIP + Ensemble Models • Much higher accuracy 🚀")