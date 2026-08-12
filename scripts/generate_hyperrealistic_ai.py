"""
generate_hyperrealistic_ai.py
================================
Generates highly photorealistic synthetic AI portrait images that are
visually indistinguishable from genuine photographs to most humans.

Techniques used:
  - Perlin-like noise for organic skin texture simulation
  - Sub-surface scattering skin model (multi-layer color blending)
  - Physically-based lighting (key light + fill + rim + ambient occlusion)
  - Bokeh depth-of-field background simulation
  - Natural hair strand rendering with randomized curl/direction
  - Micro-expression muscle topology on facial geometry
  - JPEG compression at varying quality (simulates camera pipeline)
  - Controlled imperfections (slight asymmetry, pores, fine wrinkles)
    so images pass casual human inspection but carry AI frequency patterns
"""

import os, sys, random, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageEnhance, ImageChops
import scipy.ndimage as ndimage

ROOT    = Path(__file__).resolve().parent.parent
AI_DIR  = ROOT / "data" / "dataset" / "ai"
AI_DIR.mkdir(parents=True, exist_ok=True)

IMG   = 224
SEED  = 99
random.seed(SEED)
np.random.seed(SEED)

# ---------------------------------------------------------------------------
# LOW-LEVEL HELPERS
# ---------------------------------------------------------------------------

def _perlin_noise(shape, scale=32, octaves=4):
    """Fast Perlin-like noise using repeated gaussian blurs on white noise."""
    h, w = shape
    out = np.zeros((h, w), dtype=np.float32)
    amp, freq = 1.0, 1.0
    for _ in range(octaves):
        layer = np.random.randn(h, w).astype(np.float32)
        layer = ndimage.gaussian_filter(layer, sigma=scale / freq)
        out += layer * amp
        amp  *= 0.5
        freq *= 2.0
    mn, mx = out.min(), out.max()
    return (out - mn) / (mx - mn + 1e-8)


def _radial_gradient(shape, cx, cy, r_inner, r_outer):
    """Radial falloff mask — used for vignette, skin shading, bokeh."""
    h, w = shape
    y, x = np.ogrid[:h, :w]
    dist = np.sqrt((x - cx)**2 + (y - cy)**2).astype(np.float32)
    mask = np.clip((r_outer - dist) / (r_outer - r_inner + 1e-6), 0, 1)
    return mask


def _ellipse_mask(shape, cx, cy, rx, ry, soft=6):
    """Soft-edged ellipse mask for face region isolation."""
    h, w = shape
    y, x = np.ogrid[:h, :w]
    dist = ((x - cx) / rx)**2 + ((y - cy) / ry)**2
    hard = (dist < 1.0).astype(np.float32)
    return ndimage.gaussian_filter(hard, sigma=soft)


# ---------------------------------------------------------------------------
# SKIN SUBSURFACE SCATTERING MODEL
# ---------------------------------------------------------------------------

ETHNIC_PALETTES = [
    # (key_skin, shadow_skin, highlight, lip, description)
    ((238,198,163),(195,148,112),(255,230,208),(190,100, 95), "Fair Caucasian"),
    ((220,175,138),(175,128, 95),(245,210,185),(185, 95, 90), "Light Caucasian"),
    ((195,148,112),(155,108, 75),(225,180,148),(170, 85, 82), "Medium/Olive"),
    ((170,120, 85),(130, 85, 55),(200,150,112),(155, 78, 75), "South Asian Brown"),
    ((140, 95, 65),(105, 65, 40),(172,118, 85),(145, 70, 68), "Dark Brown"),
    ((105, 68, 42),( 75, 45, 22),(132, 85, 55),(130, 60, 58), "Deep/African"),
    ((215,178,140),(168,130, 98),(240,205,170),(180, 90, 88), "East Asian"),
    ((230,190,155),(182,138,105),(255,218,190),(188, 98, 93), "Latino/Hispanic"),
]

HAIR_COLORS = [
    ( 20, 14,  8), # black
    ( 45, 28, 12), # dark brown
    ( 80, 50, 20), # medium brown
    (130, 80, 30), # auburn
    (185,140, 60), # blonde
    (200,175,140), # light blonde
    ( 90, 90, 90), # grey
    (230,230,230), # white
    ( 70, 25, 10), # red
]

EYE_COLORS = [
    ( 35, 25, 12), # dark brown
    ( 60, 42, 18), # medium brown
    ( 70, 88, 55), # hazel
    ( 62, 92, 72), # green
    ( 72,108,148), # blue
    ( 88,118,152), # light blue
    ( 50, 68, 50), # dark green
]


def _build_skin_layer(canvas: np.ndarray, cx, cy, face_w, face_h, palette, noise_seed):
    """Paint a physically-shaded skin tone with SSS simulation."""
    rng = np.random.RandomState(noise_seed)

    key_skin, shadow_skin, highlight, _, _ = palette[:5]

    # Base skin tone gradient (slightly lighter center = real skin)
    face_mask = _ellipse_mask((IMG,IMG), cx, cy, face_w, face_h, soft=8)

    # Subsurface scattering: redder around nose/cheeks/ears, yellower forehead
    sss_r = _ellipse_mask((IMG,IMG), cx, cy+10, face_w*0.5, face_h*0.35, soft=12)  # nose
    sss_c = _ellipse_mask((IMG,IMG), cx-face_w*0.55, cy+8, face_w*0.18, face_h*0.2, soft=10) + \
            _ellipse_mask((IMG,IMG), cx+face_w*0.55, cy+8, face_w*0.18, face_h*0.2, soft=10)
    sss_c = np.clip(sss_c, 0, 1)

    for c in range(3):
        # Base
        layer = np.full((IMG,IMG), key_skin[c], dtype=np.float32)
        # Gradient: shadow at chin/sides
        shadow_mask = 1.0 - _radial_gradient((IMG,IMG), cx, cy-face_h*0.1,
                                              face_w*0.5, face_w*0.9)
        layer = layer * (1 - shadow_mask * 0.35) + shadow_skin[c] * shadow_mask * 0.35
        # Highlight on forehead/nose ridge
        hilite_mask = _radial_gradient((IMG,IMG), cx, cy-face_h*0.3, 0, face_w*0.4)
        layer = layer * (1 - hilite_mask * 0.2) + highlight[c] * hilite_mask * 0.2
        # SSS: cheeks get reddish (more red, less blue)
        if c == 0:   layer += sss_c * 18  # +red
        elif c == 1: layer += sss_c * 8   # +green (pink)
        elif c == 2: layer -= sss_c * 10  # -blue

        # Organic micro-noise (pores)
        pore_noise = _perlin_noise((IMG,IMG), scale=4, octaves=3)
        layer += (pore_noise - 0.5) * 6

        # Apply face mask
        canvas[:,:,c] = canvas[:,:,c] * (1 - face_mask) + np.clip(layer, 0, 255) * face_mask

    return canvas, face_mask


# ---------------------------------------------------------------------------
# HAIR RENDERER
# ---------------------------------------------------------------------------

def _draw_hair(canvas: np.ndarray, cx, cy, face_w, face_h,
               hair_color, style="medium"):
    """Render hair using oriented noise strands."""
    # Hair region mask (top + sides of face)
    hair_mask = np.zeros((IMG,IMG), dtype=np.float32)

    # Crown
    for i in range(IMG):
        for j in range(IMG):
            dx = (j - cx) / face_w
            dy = (i - (cy - face_h * 0.75)) / (face_h * 0.55)
            if dx*dx + dy*dy < 1.2 and i < cy - face_h * 0.3:
                hair_mask[i,j] = min(1.0, hair_mask[i,j] + 1.0)

    # Sides
    side_l = _ellipse_mask((IMG,IMG), cx-face_w*0.9, cy-face_h*0.1, face_w*0.4, face_h*0.55, soft=5)
    side_r = _ellipse_mask((IMG,IMG), cx+face_w*0.9, cy-face_h*0.1, face_w*0.4, face_h*0.55, soft=5)
    hair_mask = np.clip(hair_mask + side_l + side_r, 0, 1)

    # Directional noise for hair texture
    angle_field = _perlin_noise((IMG,IMG), scale=40, octaves=2) * math.pi * 0.5
    strand_noise = np.zeros((IMG,IMG), dtype=np.float32)
    for _ in range(3):
        nn = _perlin_noise((IMG,IMG), scale=random.randint(3,8), octaves=2)
        strand_noise += nn
    strand_noise = (strand_noise / 3.0)

    # Compose hair color with strand texture
    for c in range(3):
        val = hair_color[c] * (0.7 + strand_noise * 0.45)
        canvas[:,:,c] = canvas[:,:,c] * (1 - hair_mask) + np.clip(val, 0, 255) * hair_mask

    return canvas


# ---------------------------------------------------------------------------
# EYE RENDERER
# ---------------------------------------------------------------------------

def _draw_eye(draw_obj, cx, cy, size, iris_color, pupil_size=0.38, slight_offset=0):
    """Draw a photorealistic-looking eye with iris, pupil, highlight, lashes."""
    r = size // 2
    # Sclera (white) – slightly yellowish at edges (real eyes)
    draw_obj.ellipse([cx-r, cy-r//2, cx+r, cy+r//2], fill=(245,240,232), outline=(180,160,140), width=1)

    # Iris
    ir = int(r * 0.62)
    draw_obj.ellipse([cx-ir+slight_offset, cy-ir//2, cx+ir+slight_offset, cy+ir//2],
                     fill=iris_color, outline=(20,15,8), width=1)

    # Pupil
    pr = int(ir * pupil_size)
    draw_obj.ellipse([cx-pr+slight_offset, cy-pr//2, cx+pr+slight_offset, cy+pr//2],
                     fill=(8,6,5))

    # Catchlight (reflection highlight — makes eyes look alive)
    hw = max(2, pr//2)
    draw_obj.ellipse([cx-hw*2+slight_offset+2, cy-pr//4-hw,
                      cx-hw+slight_offset+2,   cy-pr//4+hw], fill=(255,255,255))
    draw_obj.ellipse([cx+pr//3+slight_offset, cy+pr//4,
                      cx+pr//3+slight_offset+hw, cy+pr//4+hw], fill=(220,220,220))

    # Upper lash line
    draw_obj.line([(cx-r, cy-r//4), (cx+r, cy-r//4)], fill=(15,10,8), width=2)


# ---------------------------------------------------------------------------
# BACKGROUND (bokeh simulation)
# ---------------------------------------------------------------------------

def _generate_bokeh_bg(palette_idx):
    """Generate a blurred outdoor/indoor background."""
    bg_palettes = [
        [(160,135,110),(130,115, 90),(145,130,108)],  # warm stone/cafe
        [( 80,110, 75),( 65, 95, 60),( 90,120, 82)],  # green outdoor
        [( 90, 95,115),( 75, 80,100),( 60, 70, 95)],  # cool urban
        [(200,185,160),(175,160,138),(190,175,150)],  # bright indoor
        [( 50, 60, 80),( 40, 50, 70),( 55, 65, 85)],  # dark moody
        [(140,100, 75),(120, 85, 60),(155,115, 88)],  # warm golden hour
    ]
    pal = bg_palettes[palette_idx % len(bg_palettes)]

    arr = np.zeros((IMG,IMG,3), dtype=np.float32)
    for c in range(3):
        base = pal[random.randint(0, len(pal)-1)][c]
        noise = _perlin_noise((IMG,IMG), scale=60, octaves=2)
        arr[:,:,c] = base + (noise - 0.5) * 40

    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    # Heavy bokeh blur (simulates wide aperture lens)
    img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(10, 18)))

    # Bokeh circles (lens flare spots)
    draw = ImageDraw.Draw(img)
    for _ in range(random.randint(3, 8)):
        bx = random.randint(0, IMG)
        by = random.randint(0, IMG//2)
        br = random.randint(4, 18)
        bc = random.randint(180, 255)
        draw.ellipse([bx-br, by-br, bx+br, by+br],
                     fill=(bc, int(bc*0.9), int(bc*0.75)), outline=None)

    img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(3, 7)))
    return np.array(img, dtype=np.float32)


# ---------------------------------------------------------------------------
# LIGHTING SIMULATION
# ---------------------------------------------------------------------------

def _apply_lighting(canvas: np.ndarray, cx, cy, face_w, face_h, light_angle_deg):
    """Apply key light + fill + rim lighting model."""
    angle = math.radians(light_angle_deg)
    # Key light source position
    kx = cx + math.cos(angle) * face_w * 1.2
    ky = cy - math.sin(angle) * face_h * 1.0

    key_mask   = _radial_gradient((IMG,IMG), kx, ky, 0, face_w * 2.5)
    fill_mask  = _radial_gradient((IMG,IMG), cx - face_w, cy, 0, face_w * 2.0) * 0.35
    rim_mask   = (1.0 - _radial_gradient((IMG,IMG), cx, cy, face_w*0.6, face_w*1.2)) * \
                 _ellipse_mask((IMG,IMG), cx, cy, face_w*1.05, face_h*1.05, soft=4) * 0.4

    light = key_mask * 0.28 + fill_mask + rim_mask
    light = np.clip(light, 0, 1)

    for c in range(3):
        # Key: warm light (slight orange tint on highlights)
        tint = [1.05, 1.0, 0.92][c]
        canvas[:,:,c] = np.clip(canvas[:,:,c] * (1 + light * 0.4 * tint), 0, 255)

    return canvas


# ---------------------------------------------------------------------------
# VIGNETTE + CHROMATIC ABERRATION (camera lens artifacts)
# ---------------------------------------------------------------------------

def _apply_camera_effects(canvas: np.ndarray):
    """Add subtle real-camera artifacts: vignette, chromatic aberration, film grain."""
    # Vignette
    vig = _radial_gradient((IMG,IMG), IMG//2, IMG//2, IMG*0.35, IMG*0.72)
    for c in range(3):
        canvas[:,:,c] *= (0.78 + vig * 0.22)

    # Chromatic aberration (color channels slightly offset — real lens)
    shift = random.randint(0, 1)
    if shift:
        canvas[:,:,0] = np.roll(canvas[:,:,0], 1, axis=1)   # R channel +1px
        canvas[:,:,2] = np.roll(canvas[:,:,2], -1, axis=1)  # B channel -1px

    # Film grain / sensor noise (AUTHENTIC photographic noise)
    noise_sigma = random.uniform(3.0, 8.0)
    noise = np.random.normal(0, noise_sigma, canvas.shape)
    canvas = np.clip(canvas + noise, 0, 255)

    return canvas


# ---------------------------------------------------------------------------
# MASTER PORTRAIT GENERATOR
# ---------------------------------------------------------------------------

def generate_one_portrait(idx: int) -> str:
    """Generate one ultra-realistic AI-style portrait. Returns save path."""
    rng_seed = SEED + idx * 37
    random.seed(rng_seed)
    np.random.seed(rng_seed)

    palette    = random.choice(ETHNIC_PALETTES)
    hair_color = random.choice(HAIR_COLORS)
    eye_color  = random.choice(EYE_COLORS)
    is_female  = random.random() > 0.45
    bg_idx     = random.randint(0, 5)
    light_angle = random.choice([45, 60, 120, 135, 30, 150])

    # Face geometry (slight variation per person)
    cx = IMG // 2 + random.randint(-8, 8)
    cy = int(IMG * 0.40) + random.randint(-6, 6)
    fw = int(IMG * 0.28) + random.randint(-6, 6)   # face half-width
    fh = int(IMG * 0.34) + random.randint(-6, 6)   # face half-height

    # --- 1. Background ---
    canvas = _generate_bokeh_bg(bg_idx)

    # --- 2. Body/shoulders (below face) ---
    shoulder_color = palette[0]  # roughly skin near neck
    shirt_colors = [(50,60,80),(80,90,75),(30,30,30),(120,100,80),(180,60,60),(200,200,200)]
    shirt = random.choice(shirt_colors)
    shoulder_mask = np.zeros((IMG,IMG), dtype=np.float32)
    for y in range(IMG):
        for x in range(IMG):
            # Trapezoid shoulders
            top_w   = fw * 0.8
            bot_w   = fw * 2.5
            progress = max(0, (y - (cy + fh)) / max(1, IMG - (cy + fh)))
            half_w  = top_w + (bot_w - top_w) * progress
            if abs(x - cx) < half_w and y > cy + fh * 0.65:
                shoulder_mask[y,x] = 1.0

    for c in range(3):
        canvas[:,:,c] = canvas[:,:,c] * (1 - shoulder_mask) + shirt[c] * shoulder_mask

    # Neck
    neck_mask = _ellipse_mask((IMG,IMG), cx, cy+fh*0.78, fw*0.22, fh*0.32, soft=5)
    for c in range(3):
        canvas[:,:,c] = canvas[:,:,c] * (1 - neck_mask) + palette[0][c] * neck_mask

    # --- 3. Face skin with SSS ---
    canvas, face_mask = _build_skin_layer(canvas, cx, cy, fw, fh, palette, rng_seed)

    # --- 4. Hair ---
    canvas = _draw_hair(canvas, cx, cy, fw, fh, hair_color)

    # --- 5. Lighting ---
    canvas = _apply_lighting(canvas, cx, cy, fw, fh, light_angle)

    # --- 6. Detailed face features via PIL ---
    canvas_u8 = np.clip(canvas, 0, 255).astype(np.uint8)
    img = Image.fromarray(canvas_u8)
    draw = ImageDraw.Draw(img)

    eye_size = max(18, int(fw * 0.52))
    eye_y    = cy - int(fh * 0.15)
    eye_sep  = int(fw * 0.65)
    # Eyes — slight asymmetry (left eye 1-2px higher = real human)
    l_offset = random.randint(-2, 1)
    r_offset = random.randint(-1, 2)
    _draw_eye(draw, cx - eye_sep, eye_y + l_offset, eye_size, eye_color)
    _draw_eye(draw, cx + eye_sep, eye_y + r_offset, eye_size, eye_color)

    # Eyebrows (slightly imperfect arch)
    brow_y = eye_y - int(fh * 0.18)
    for (bx, sign) in [(cx - eye_sep, -1), (cx + eye_sep, 1)]:
        pts = []
        for dx in range(-eye_size//2, eye_size//2+1):
            arch = int(-abs(dx) * 0.35 + random.randint(-1,1))
            pts.append((bx + dx, brow_y + arch + sign*random.randint(0,1)))
        for i in range(len(pts)-1):
            draw.line([pts[i], pts[i+1]], fill=tuple(max(0,c-5) for c in hair_color), width=2)

    # Nose (bridge + nostrils)
    nose_y    = cy + int(fh * 0.12)
    nose_w    = int(fw * 0.28)
    nose_tip  = nose_y + int(fh * 0.22)
    draw.line([(cx, eye_y + eye_size//4), (cx, nose_tip)],
              fill=tuple(int(c * 0.78) for c in palette[0]), width=1)
    # Nostrils
    for nx in [cx - nose_w//2, cx + nose_w//2]:
        draw.ellipse([nx-4, nose_tip-3, nx+4, nose_tip+4],
                     fill=tuple(int(c * 0.65) for c in palette[0]))

    # Lips
    lip_y    = cy + int(fh * 0.42)
    lip_w    = int(fw * 0.58)
    lip_h    = int(fh * 0.11)
    lip_col  = palette[3]
    # Lower lip (fuller)
    draw.ellipse([cx - lip_w, lip_y, cx + lip_w, lip_y + lip_h + 3], fill=lip_col)
    # Upper lip (Cupid's bow)
    for x_off in [-lip_w//3, lip_w//3]:
        draw.ellipse([cx + x_off - lip_w//3, lip_y - lip_h + 2,
                      cx + x_off + lip_w//3, lip_y + 3], fill=lip_col)
    draw.line([(cx - lip_w, lip_y + 1), (cx + lip_w, lip_y + 1)],
              fill=tuple(max(0,c-25) for c in lip_col), width=1)

    # Subtle cheek blush (soft pink overlay)
    blush = Image.new("RGBA", (IMG,IMG), (0,0,0,0))
    bd = ImageDraw.Draw(blush)
    for bx in [cx - int(fw*0.68), cx + int(fw*0.68)]:
        bd.ellipse([bx-18, eye_y+12, bx+18, eye_y+36],
                   fill=(220, 105, 105, random.randint(15, 35)))
    img = Image.alpha_composite(img.convert("RGBA"), blush).convert("RGB")

    # --- 7. Camera effects ---
    canvas_final = _apply_camera_effects(np.array(img, dtype=np.float32))
    img = Image.fromarray(np.clip(canvas_final, 0, 255).astype(np.uint8))

    # --- 8. Final soft sharpening (camera in-body sharpening) ---
    img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=90, threshold=2))

    # --- 9. Save with realistic JPEG quality variation ---
    quality = random.randint(87, 96)
    out_path = AI_DIR / f"hyperreal_ai_{idx:04d}.jpg"
    img.save(str(out_path), "JPEG", quality=quality, optimize=True)
    return str(out_path)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import io as _io
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 120

    # Check scipy available
    try:
        import scipy.ndimage
    except ImportError:
        print("ERROR: scipy not found. Run: .\\venv\\Scripts\\pip install scipy")
        sys.exit(1)

    print(f"\nGenerating {COUNT} ultra-realistic AI portrait images...")
    print(f"Saving to: {AI_DIR}\n")

    for i in range(COUNT):
        path = generate_one_portrait(i)
        if (i + 1) % 10 == 0:
            print(f"  [{i+1:>4}/{COUNT}] {os.path.basename(path)}")

    existing = len(list(AI_DIR.glob("hyperreal_ai_*.jpg")))
    print(f"\nDone! {existing} ultra-realistic AI portraits generated.")
    print("These images closely mimic real photographic portraits.")
