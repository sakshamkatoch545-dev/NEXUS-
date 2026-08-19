import sys, os, glob
from PIL import Image
sys.path.append('.')
from src.detector import full_image_analysis

folder = r"C:\Users\saksh\.gemini\antigravity-ide\brain\87826ea9-0d35-4429-aeae-81ccc2c90e3a\.user_uploaded"
images = sorted(glob.glob(os.path.join(folder, "*.jpg")))

for img_path in images:
    img = Image.open(img_path).convert('RGB')
    res = full_image_analysis(img)
    print("=" * 60)
    print(f"FILE: {os.path.basename(img_path)}")
    print(f"VERDICT: {res['verdict']} | AI Score: {res['confidence_score']}% | Human Score: {res['human_score']}%")
    print(f"Judge Verdict: {res['judge_verdict']} | Judge Score: {res['judge_score']}")
    print("-" * 60)
    for k, v in res['engines'].items():
        print(f"{k:25}: score={v.get('score', 'N/A')}/{v.get('max', 'N/A')} (raw={v.get('raw', 'N/A')})")

