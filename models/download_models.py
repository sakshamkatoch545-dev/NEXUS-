"""
download_models.py — Robust Offline Pretrained Model Downloader
==============================================================
Downloads verified model weights and configs from Hugging Face into models/cache/,
verifies non-empty file integrity, logs licenses, and supports resuming.
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure UTF-8 stdout on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure parent and current directory are on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from registry import MODEL_REGISTRY, ModelSpec, CACHE_DIR

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    hf_hub_download = None


def download_file_hf(repo_id: str, filename: str, target_dir: Path) -> Tuple[bool, str, int]:
    """
    Downloads a single file from Hugging Face Hub into target_dir.
    Returns (success, message, file_size_bytes).
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / Path(filename).name

    # Check if already present and valid
    if destination.exists() and destination.stat().st_size > 0:
        return True, "Already cached locally", destination.stat().st_size

    if hf_hub_download is None:
        return False, "huggingface_hub library not installed", 0

    try:
        # Download with local copy into destination
        downloaded_temp_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=target_dir,
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        
        # Verify file exists and is not empty
        target_path = Path(downloaded_temp_path)
        if target_path.exists() and target_path.stat().st_size > 0:
            return True, "Successfully downloaded", target_path.stat().st_size
        else:
            return False, "Downloaded file is empty", 0

    except Exception as exc:
        err_msg = str(exc)
        if "404 Client Error" in err_msg or "Entry Not Found" in err_msg:
            return False, "File does not exist on Hugging Face Hub (missing upstream)", 0
        return False, f"Download error: {err_msg}", 0


def download_model(spec: ModelSpec, force: bool = False) -> Dict[str, any]:
    """Downloads all required files for a specific ModelSpec."""
    result = {
        "id": spec.repo_id,
        "name": spec.name,
        "license": spec.license,
        "commercial_use": spec.commercial_use,
        "status": "FAILED",
        "message": "",
        "local_path": str(spec.primary_weight_path),
        "size_mb": 0.0,
    }

    if not spec.enabled:
        result["status"] = "SKIPPED"
        result["message"] = spec.notes or "Model disabled in registry"
        return result

    if not force and spec.is_cached():
        result["status"] = "ALREADY_CACHED"
        result["message"] = "Verified existing weights"
        result["size_mb"] = spec.primary_weight_path.stat().st_size / (1024 * 1024)
        return result

    print(f"\n[DOWNLOAD] Fetching {spec.name} ({spec.repo_id}) ...")
    print(f"           License: {spec.license} (Commercial: {'YES' if spec.commercial_use else 'NO/RESEARCH ONLY'})")

    # Download primary weights
    success, msg, size_bytes = download_file_hf(spec.repo_id, spec.filename, spec.local_dir)
    if not success:
        result["status"] = "FAILED"
        result["message"] = msg
        print(f"           [FAILED] Primary weight: {msg}", flush=True)
        return result

    # Download any extra configs (e.g. config.json, preprocessor_config.json)
    for extra_file in spec.extra_files:
        ok_extra, msg_extra, _ = download_file_hf(spec.repo_id, extra_file, spec.local_dir)
        if not ok_extra:
            print(f"           [WARN] Extra file '{extra_file}' could not be fetched ({msg_extra})", flush=True)

    result["status"] = "DOWNLOADED"
    result["message"] = "Download complete and verified"
    result["size_mb"] = size_bytes / (1024 * 1024)
    print(f"           [SUCCESS] Downloaded {result['size_mb']:.1f} MB -> {spec.primary_weight_path}", flush=True)
    return result


def download_all_models(model_id_filter: str = None, force: bool = False):
    """Downloads all enabled models or a specific targeted model."""
    print("=" * 80, flush=True)
    print(" NEXUS+ PRETRAINED DETECTION MODELS DOWNLOADER ", flush=True)
    print("=" * 80, flush=True)
    print(f"Target Cache Directory: {CACHE_DIR.resolve()}\n", flush=True)

    targets = []
    if model_id_filter:
        if model_id_filter in MODEL_REGISTRY:
            targets.append((model_id_filter, MODEL_REGISTRY[model_id_filter]))
        else:
            print(f"[ERROR] Unknown model identifier '{model_id_filter}'. Available keys: {list(MODEL_REGISTRY.keys())}", flush=True)
            sys.exit(1)
    else:
        targets = list(MODEL_REGISTRY.items())

    results = []
    for model_key, spec in targets:
        res = download_model(spec, force=force)
        res["key"] = model_key
        results.append(res)

    print("\n" + "=" * 80)
    print(" DOWNLOAD SUMMARY ")
    print("=" * 80)
    print(f"{'Model Key':<22} | {'Status':<14} | {'License':<10} | {'Size (MB)':<9} | {'Details'}")
    print("-" * 80)

    downloaded_cnt = 0
    cached_cnt = 0
    skipped_cnt = 0
    failed_cnt = 0

    for r in results:
        status_str = r["status"]
        if status_str == "DOWNLOADED":
            downloaded_cnt += 1
        elif status_str == "ALREADY_CACHED":
            cached_cnt += 1
        elif status_str == "SKIPPED":
            skipped_cnt += 1
        else:
            failed_cnt += 1

        print(f"{r['key']:<22} | {status_str:<14} | {r['license']:<10} | {r['size_mb']:>7.1f} MB | {r['message']}")

    print("-" * 80)
    print(f"Total: {len(results)} | Downloaded: {downloaded_cnt} | Already Cached: {cached_cnt} | Skipped: {skipped_cnt} | Failed: {failed_cnt}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download pretrained AI image detection models locally.")
    parser.add_argument("--model", type=str, default=None, help="Download only a specific model key (e.g. capcheck_vit)")
    parser.add_argument("--force", action="store_true", help="Force re-download even if already cached")
    args = parser.parse_args()

    download_all_models(model_id_filter=args.model, force=args.force)
