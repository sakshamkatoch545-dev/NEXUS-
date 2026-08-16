# AI Image Detector (original implementation, college project)

An original, from-scratch AI-generated-image detector built from **publicly
documented** forensic image-analysis and machine-learning techniques —
FFT/DCT frequency analysis, noise-residual statistics, edge/texture
statistics, and a pretrained open vision backbone (CLIP) for deep
embeddings, fused and fed into a calibrated classifier.

This is **not** a copy, reverse-engineering, or reproduction of any
commercial detector's source code or model weights, and it makes no claim
of matching any specific commercial product's accuracy.

## Architecture

```
IMAGE → preprocessing → compression-aware normalization → forensic feature
extraction + deep visual embedding → feature fusion → trained classifier
→ probability calibration → structured verdict
```

## Files

| File              | Purpose                                              |
|-------------------|-------------------------------------------------------|
| `config.py`       | All settings (paths, thresholds, model hyperparams)  |
| `preprocessing.py`| Image loading, RGB conversion, compression-aware prep|
| `features.py`     | Forensic features + optional CLIP deep embeddings    |
| `calibration.py`  | Platt scaling / isotonic probability calibration     |
| `detector.py`     | `AIImageDetector` — the main inference entry point    |
| `train.py`        | Training pipeline, with duplicate/leakage prevention |
| `evaluate.py`     | Metrics, robustness tests, unseen-generator reporting|

## Setup

```bash
pip install -r requirements.txt
```

`torch` + `transformers` are optional. If they're missing or the CLIP
weights can't be downloaded, the detector automatically falls back to
forensic-features-only mode and says so in its `warnings`.

## 1. Add training data

Populate these folders with your own labeled images (you must supply a
dataset — none is bundled):

```
data/train/real/       genuine photographs
data/train/ai/         AI-generated images
data/validation/real/
data/validation/ai/
data/test/real/
data/test/ai/
```

For leakage-safe splitting, name files with a `source__` prefix, e.g.
`midjourney__0001.png`, `dslr_batch3__0002.jpg`. Files sharing a prefix are
treated as one "group" and validation/test groups that also appear in
training are dropped automatically. Near-duplicate images (perceptual hash)
are de-duplicated before training as well.

## 2. Train

```bash
python train.py --root . --classifier gradient_boosting
```

Produces `models/classifier.joblib`, `models/calibrator.joblib`,
`models/feature_scaler.joblib`, and `models/model_metadata.json` (which
records how many samples were used, so you can gauge how much to trust the
numbers — a 40-image toy set is not a validated detector).

## 3. Evaluate

```bash
python evaluate.py --root . --split test --unseen-generators midjourney,dalle3
```

Writes `results/evaluation_test.json` with accuracy / precision / recall /
F1 / ROC-AUC / confusion matrix / false-positive & false-negative rates,
plus:
- known-generator vs. unseen-generator performance,
- performance under JPEG recompression and screenshot-like transforms,
- robustness: how much the AI-probability shifts under benign transforms
  (JPEG compression, resize, crop, brightness, blur) that should not flip a
  correct verdict.

## 4. Use it

```python
from detector import AIImageDetector

detector = AIImageDetector()
result = detector.predict("some_image.jpg")
print(result.to_json())
```

Output shape:

```json
{
  "ai_probability": 0.0,
  "human_probability": 0.0,
  "confidence": 0.0,
  "verdict": "AI | HUMAN | UNCERTAIN",
  "signals": ["..."],
  "warnings": ["..."]
}
```

## Honest limitations (read before writing up the project)

- **No dataset is bundled.** The detector is only as good as what you train
  it on. A handful of images will not produce a scientifically valid
  detector — say so explicitly in any report.
- **Not equivalent to any commercial product.** Numbers are measured only
  on your own supplied dataset and will not generalize automatically.
- **Generator coverage matters.** A generator absent from training data
  will likely be detected worse — this is why `evaluate.py` supports
  separate known/unseen-generator reporting; report both.
- **False positives matter.** Real photos, especially edited or heavily
  compressed ones, can be misclassified. The false-positive rate is
  reported explicitly and should be highlighted alongside accuracy.
- Every `predict()` result carries `warnings` describing exactly these
  caveats — don't strip them out when presenting results.
