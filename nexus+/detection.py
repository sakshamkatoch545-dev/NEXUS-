"""
detection.py / detector.py
==========================
Main entry point for AI-generated and AI-edited image detection.
Original implementation inspired by modern multi-stage AI content detectors.

Supports:
- 100% Synthetic / AI-generated image detection
- Real photograph verification
- Real-but-AI-Edited / Inpainted / Retouched image detection (like ZeroGPT / GPTZero)
- Real-time progress tracking
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

_CUR_DIR = Path(__file__).resolve().parent
_AI_DETECTOR_DIR = _CUR_DIR.parent / "ai_image_detector"

for p in [str(_CUR_DIR), str(_AI_DETECTOR_DIR)]:
    if p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)

from detector import AIImageDetector, DetectionResult, _SIGNAL_DESCRIPTIONS, _cli_progress_bar  # noqa: E402

__all__ = ["AIImageDetector", "DetectionResult", "_SIGNAL_DESCRIPTIONS", "_cli_progress_bar"]

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    if len(sys.argv) < 2:
        print("Usage: python detection.py <image_path>")
        sys.exit(1)

    print(f"\n[SCAN] Analyzing image with AI Image Detector: {sys.argv[1]}")
    detector = AIImageDetector()
    res = detector.predict(sys.argv[1], progress_callback=_cli_progress_bar)
    print("\n--- STRUCTURED VERDICT ---")
    print(res.to_json(indent=2))
