# NEXUS+ reconstruction specification

Give this file to an engineer or coding agent together with the repository when
the project must be rebuilt with the same behavior and layout.

## Non-negotiable constraints

- Do not change `app.py` behavior, UI structure, engine order, scoring keys, or
  legacy API compatibility.
- Do not change `README.md` unless explicitly requested.
- Use Python 3.12, install every package in `requirements.txt`, and keep the
  installed package versions consistent across machines.
- Use `requirements.lock` when pinned builds are available for the target
  operating system and Python version.
- Do not commit API keys, `.env`, `venv`, `.runtime_packages`, Python caches, or
  local backup/candidate model directories.
- Preserve the tracked `fine_tuned_vit` checkpoint and the tracked dataset,
  sample images, scripts, and screenshots.
- Install Git LFS before cloning so `fine_tuned_vit/model.safetensors` is
  downloaded instead of remaining an LFS pointer.

## Runtime contract

The entry point is `app.py`, launched with `streamlit run app.py`. The detector
entry point is `src.detector.full_image_analysis(PIL.Image)`. The legacy profile
entry point is `src.detector.full_profile_analysis(...)`.

The detector returns the existing verdict and engine fields plus structured
fields including `ai_probability`, `real_probability`, `confidence`,
`nearest_generator`, `similarity`, `detected_artifacts`, `feature_scores`,
`reason`, and `top_matches`.

The current 13-engine order is:

1. Neural Network Ensemble
2. CLIP Semantic Analysis
3. Texture Smoothness
4. Color & Saturation
5. Frequency Domain FFT
6. Background & Edge
7. Portrait Style
8. Gemini / Groq Vision Forensics
9. Face Symmetry & Smoothness
10. Error Level Analysis
11. Fine-Tuned ViT Classifier
12. Watermark Detection
13. ChatGPT / Gemini Provenance

## Fresh-machine build

```powershell
git lfs install
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements.lock
$env:GEMINI_API_KEY = "your-own-key"
$env:GROQ_API_KEY = "your-own-key"
streamlit run app.py
```

The equivalent automated command is:

```powershell
.\scripts\setup.ps1
```

## API behavior

Use the user’s own Gemini and Groq keys. Read them only from
`GEMINI_API_KEY` and `GROQ_API_KEY`. Gemini is attempted first, then Groq Vision
fallbacks. Never place real credentials in source code or commit history.

## Copy-paste reconstruction prompt

> Rebuild the NEXUS+ repository from this checkout exactly. Read
> `REBUILD_SPEC.md`, `SETUP.md`, `.env.example`, `requirements.txt`, `app.py`,
> and every file under `src/`, `scripts/`, `files/`, `data/`, `sample_images/`,
> and `fine_tuned_vit/` before editing. Preserve the README and all existing
> features. Do not rename or duplicate files. Use Python 3.12 and install all
> dependencies from `requirements.txt`, then use `requirements.lock` for pinned
> versions when compatible wheels exist. Preserve the 13-engine order and the
> public return schema. Keep the tracked fine-tuned model and dataset. Configure
> API keys only through environment variables. Run syntax checks and a local
> Streamlit smoke test before reporting completion. If exact API results differ,
> explain that provider model versions are external and keep local inference
> deterministic.

Exact API output cannot be guaranteed because Gemini and Groq are external
services whose model versions and responses can change. Local output is
reproducible when the same image bytes, checkpoint, dependency versions, and
hardware/runtime are used.
