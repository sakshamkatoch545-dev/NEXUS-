import sys, os
from PIL import Image
sys.path.append('.')
from src.detector import full_image_analysis

img_path = r"C:\Users\saksh\.gemini\antigravity-ide\brain\d11483c8-d3b2-4beb-b63f-af44d4e49e04\.user_uploaded\media_1786784315986.jpg"
img = Image.open(img_path).convert('RGB')
res = full_image_analysis(img)
print(f"VERDICT: {res['verdict']} | AI Score: {res['confidence_score']}% | Human Score: {res['human_score']}%")
print("-" * 70)
for k, v in res['engines'].items():
    print(f"{k:25}: score={v['score']}/{v['max']} (raw={v.get('raw', 0):.2f}) | {v['explanation']}")
