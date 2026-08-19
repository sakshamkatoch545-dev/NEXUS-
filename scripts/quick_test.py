import sys, os
from PIL import Image
sys.path.append('.')
from src.detector import full_image_analysis

img_path = r"C:\Users\saksh\.gemini\antigravity-ide\brain\03e951ae-f00f-4eab-bba5-2db8fd59fcf7\.user_uploaded\media_1787146738092.jpg"
img = Image.open(img_path).convert('RGB')
res = full_image_analysis(img)

print("=" * 60)
print(f"VERDICT: {res['verdict']}")
print(f"Human (Real) Authenticity: {res['human_score']}%")
print(f"AI Threat Score: {res['confidence_score']}%")
print(f"Judge Consensus: {res['judge_verdict']} (Score: {res['judge_score']})")
print("-" * 60)
for k, v in res['engines'].items():
    print(f"  {k:22}: score={v.get('score', 0)}/{v.get('max', 100)}")
