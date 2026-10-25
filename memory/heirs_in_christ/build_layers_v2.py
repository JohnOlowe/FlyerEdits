#!/usr/bin/env python3
"""
Heirs in Christ - 1280x800 Background v2 (REFINED)
Fixes: hard glow ring, flat halftone, missing warm/purple edge tints, missing horizon light
Layer by layer, each stage saved as its own file.
"""
from PIL import Image, ImageDraw, ImageFilter
import numpy as np, math, os

W, H = 1280, 800
out_dir = "/home/user/memory/heirs_in_christ"
os.makedirs(f"{out_dir}/layers2", exist_ok=True)
os.makedirs(f"{out_dir}/final2", exist_ok=True)

def save(img, name, folder):
    p = f"{out_dir}/{folder}/{name}"
    img.save(p, "PNG")
    print("saved", p, img.size)

def smoothstep(k):
    k = np.clip(np.asarray(k, dtype=np.float32), 0.0, 1.0)
    return k*k*(3-2*k)

def lerp(a, b, k):
    return a + (b-a)*k  # works for scalars and numpy arrays

# ============================================================
# LAYER 01 - BASE SKY GRADIENT  (cyan top -> blue -> luminous bottom)
# ============================================================
print("L01 base gradient")
arr = np.zeros((H, W, 3), dtype=np.float32)
yy, xx = np.mgrid[0:H, 0:W]
t = yy / (H-1)          # 0 top .. 1 bottom

# key colours sampled from flyer
C = [
    (0.00, (0x1E, 0xC4, 0xEC)),   # bright cyan
    (0.28, (0x15, 0x9B, 0xD2)),   # sky blue
    (0.52, (0x1B, 0x62, 0xA8)),   # deep blue
    (0.72, (0x24, 0x4B, 0x93)),   # navy
    (0.88, (0x8E, 0x9A, 0xC8)),   # haze
    (1.00, (0xE6, 0xE4, 0xEE)),   # pale bottom
]
for i in range(len(C)-1):
    t0, c0 = C[i]; t1, c1 = C[i+1]
    m = (t >= t0) & (t <= t1)
    k = smoothstep((t[m] - t0) / max(1e-6, (t1-t0)))
    for ch in range(3):
        arr[..., ch][m] = lerp(c0[ch], c1[ch], k)

# horizontal tint: slightly teal on left, slightly violet-blue on right
hx = xx / (W-1)
arr[..., 0] += (hx - 0.5) * 10     # a touch more red on right
arr[..., 1] += (hx - 0.5) * -6
arr[..., 2] += (hx - 0.5) * 14

arr = np.clip(arr, 0, 255).astype(np.uint8)
base = Image.fromarray(arr, "RGB").filter(ImageFilter.GaussianBlur(2.0))
save(base, "01_base_gradient.png", "layers2")
comp = base.copy()
save(comp, "01_composite.png", "final2")

# ============================================================
# LAYER 02 - HALFTONE DOT TEXTURE (warm left, violet right)
# ============================================================
print("L02 halftone")
S = 2  # supersample for crisp anti-aliased dots
hs = Image.new("RGBA", (W*S, H*S), (0, 0, 0, 0))
hd = ImageDraw.Draw(hs)

spacing = 9.0
nx, ny = int(W/spacing)+1, int(H/spacing)+1
for j in range(ny):
    for i in range(nx):
        # brick/rotated grid like a real print screen
        cx = i*spacing + (spacing*0.5 if j % 2 else 0)
        cy = j*spacing*0.87
        if cx > W or cy > H:
            continue

        fx, fy = cx/W, cy/H

        # ---- LEFT warm zone (red/orange) ----
        left = smoothstep((0.34 - fx) / 0.34) if fx < 0.34 else 0.0
        left *= (0.35 + 0.65*smoothstep(fy/0.85))
        # ---- RIGHT violet zone ----
        right = smoothstep((fx - 0.66) / 0.34) if fx > 0.66 else 0.0
        right *= (0.40 + 0.60*smoothstep(fy/0.85))
        # ---- TOP subtle zone ----
        top = smoothstep((0.16 - fy)/0.16) * 0.35 * (0.55 + 0.45*math.sin(fx*7.0))

        s = max(left, right, top)
        if s < 0.06:
            continue

        # dot size grows with zone strength, tiny fade-in at inner border
        r = spacing * 0.52 * (s**0.75)
        if r < 0.45:
            continue

        if left >= right and left >= top:
            # warm white dots over red/orange
            col = (255, int(240 - 20*s), int(225 - 40*s))
        elif right >= top:
            # cool white dots over violet
            col = (int(235 + 20*s), int(225 + 10*s), 255)
        else:
            col = (255, 255, 255)

        a = int(200 * s)
        hd.ellipse([(cx-r)*S, (cy-r)*S, (cx+r)*S, (cy+r)*S], fill=col + (a,))

halftone = hs.resize((W, H), Image.LANCZOS)

# coloured wash UNDER the dots so it reads as tinted halftone, not white noise
wash = np.zeros((H, W, 3), dtype=np.float32)
alpha = np.zeros((H, W), dtype=np.float32)

fx = xx/(W-1); fy = yy/(H-1)
leftm = np.clip((0.42 - fx)/0.42, 0, 1)**1.6
leftm *= (0.30 + 0.70*np.clip(fy/0.9, 0, 1))
rightm = np.clip((fx - 0.58)/0.42, 0, 1)**1.6
rightm *= (0.30 + 0.70*np.clip(fy/0.9, 0, 1))

# warm: #F0644B -> #E23A2A
wash[..., 0] = 240*leftm + 150*rightm
wash[..., 1] = 100*leftm + 60*rightm
wash[..., 2] = 75*leftm + 175*rightm
alpha = np.clip(leftm*0.55 + rightm*0.55, 0, 0.75)

wash_img = Image.fromarray(np.dstack([np.clip(wash,0,255), alpha*255]).astype(np.uint8), "RGBA")
wash_img = wash_img.filter(ImageFilter.GaussianBlur(14))

halftone_layer = Image.alpha_composite(wash_img, halftone)
save(halftone_layer, "02_halftone_overlay.png", "layers2")

comp = Image.alpha_composite(comp.convert("RGBA"), halftone_layer).convert("RGB")
save(comp, "02_composite.png", "final2")

# ============================================================
# LAYER 03 - CLOUDS / ATMOSPHERE  (no visible ellipse edges)
# ============================================================
print("L03 clouds")
cloud_acc = np.zeros((H, W), dtype=np.float32)

def puff(cx, cy, rx, ry, strength):
    dx = (xx - cx) / rx
    dy = (yy - cy) / ry
    d = np.sqrt(dx*dx + dy*dy)
    return strength * np.clip(1.0 - d, 0, 1)**1.7

# whispy horizon clouds (upper area, like flyer)
puffs = [
    (170, 120, 330,  70, 0.55), (300,  95, 180,  45, 0.35),
    (700, 150, 300,  60, 0.40), (980, 130, 260,  55, 0.35),
    (1080, 330, 330,  85, 0.55), (1230, 300, 200, 60, 0.45),
    (900, 470, 300,  70, 0.40),
    (150, 430, 260,  70, 0.35),
    (300, 560, 420, 110, 0.50),
    (700, 540, 460, 100, 0.45),
    (1050, 590, 400, 120, 0.50),
    (640, 700, 700, 130, 0.55),
]
for p in puffs:
    cloud_acc += puff(*p)

cloud_acc = np.clip(cloud_acc, 0, 1)
cloud_img = Image.fromarray((cloud_acc*255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(26))

# clouds are luminous white-blue
cloud_rgba = Image.new("RGBA", (W, H), (255, 255, 255, 0))
ca = np.array(cloud_img).astype(np.float32) / 255.0
rgba = np.zeros((H, W, 4), dtype=np.uint8)
rgba[..., 0] = 255
rgba[..., 1] = 252
rgba[..., 2] = 255
rgba[..., 3] = (ca * 150).astype(np.uint8)
cloud_layer = Image.fromarray(rgba, "RGBA")
cloud_layer = Image.composite(cloud_layer, Image.new("RGBA",(W,H),(0,0,0,0)), cloud_img.point(lambda v: min(255, v*2)))
save(cloud_layer, "03_clouds_overlay.png", "layers2")

comp = Image.alpha_composite(comp.convert("RGBA"), cloud_layer).convert("RGB")
save(comp, "03_composite.png", "final2")

# ============================================================
# LAYER 04 - CENTRAL HEAVENLY BLOOM (soft, NO hard ring)
# ============================================================
print("L04 bloom")
gx, gy = W*0.50, H*0.62
dx = (xx - gx) / (W*0.55)
dy = (yy - gy) / (H*0.80)
d = np.sqrt(dx*dx + dy*dy)

# multi-octave soft falloff = organic bloom with zero banding
bloom = np.zeros((H, W), dtype=np.float32)
for w, s in [(1.00, 0.55), (0.62, 0.32), (0.36, 0.26), (0.18, 0.24)]:
    bloom += s * np.clip(1.0 - d/w, 0, 1)**2.2

# vertical light shaft rising from the horizon (as in flyer)
shaft = np.clip(1.0 - np.abs(xx - W*0.5)/(W*0.34), 0, 1)**2.0
shaft *= np.clip(1.0 - (H*0.72 - yy)/(H*0.72), 0, 1)**0.6
shaft *= np.where(yy > H*0.28, 1.0, 0.0)
bloom = np.clip(bloom + shaft*0.35, 0, 1.6)

bloom = bloom / bloom.max()
rgba = np.zeros((H, W, 4), dtype=np.uint8)
rgba[..., 0] = 255
rgba[..., 1] = np.clip(248 - 10*(1-bloom), 0, 255).astype(np.uint8)
rgba[..., 2] = np.clip(236 - 30*(1-bloom), 0, 255).astype(np.uint8)
rgba[..., 3] = (np.clip(bloom, 0, 1)**1.25 * 235).astype(np.uint8)
bloom_img = Image.fromarray(rgba, "RGBA").filter(ImageFilter.GaussianBlur(3))
save(bloom_img, "04_bloom_overlay.png", "layers2")

comp = Image.alpha_composite(comp.convert("RGBA"), bloom_img).convert("RGB")
save(comp, "04_composite.png", "final2")

# ============================================================
# LAYER 05 - DEPTH VIGNETTE + GRAIN + FINAL GRADE
# ============================================================
print("L05 grade")
a = np.array(comp).astype(np.float32)

# vignette
nx = (xx - W/2)/(W/2); ny = (yy - H/2)/(H/2)
vd = np.sqrt(nx*nx*0.55 + ny*ny*0.85)
vig = np.clip((vd - 0.55)/0.75, 0, 1)**1.8
for ch, tint in enumerate((18, 26, 62)):
    a[..., ch] = a[..., ch]*(1-vig*0.30) + tint*vig*0.30*vig

# gentle S-curve contrast
x = a/255.0
x = np.where(x < 0.5, 0.5*(2*x)**1.06, 1-0.5*(2*(1-x))**1.06)
a = x*255.0

# faint film grain to kill banding on projectors
rng = np.random.default_rng(7)
grain = rng.normal(0, 2.6, (H, W, 1))
a = np.clip(a + grain, 0, 255)

final = Image.fromarray(a.astype(np.uint8), "RGB")
save(final, "05_FINAL_background.png", "final2")

# export copies
final.save(f"{out_dir}/background_1280x800.png", "PNG")
final.save(f"{out_dir}/background_1280x800.jpg", "JPEG", quality=96, subsampling=0)
os.makedirs("/home/user/memory/renders", exist_ok=True)
final.save("/home/user/memory/renders/heirs_background_1280x800.png", "PNG")
print("\nDONE", final.size)
