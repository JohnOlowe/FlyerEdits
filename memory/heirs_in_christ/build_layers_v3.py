#!/usr/bin/env python3
"""
Heirs in Christ - 1280x800 BACKGROUND v3
Fixes vs v2: halftone far too coarse/dense, hard cut-off line at 87% height,
bloom read as a point light instead of a heavenly burst, clouds invisible.
"""
from PIL import Image, ImageDraw, ImageFilter
import numpy as np, os

W, H = 1280, 800
out = "/home/user/memory/heirs_in_christ"
os.makedirs(f"{out}/layers3", exist_ok=True)
os.makedirs(f"{out}/final3", exist_ok=True)

def save(img, name, folder):
    p = f"{out}/{folder}/{name}"
    img.save(p, "PNG")
    print("saved", p)

def ss(k):
    k = np.clip(np.asarray(k, np.float32), 0, 1)
    return k*k*(3-2*k)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
fx = xx / (W-1)
fy = yy / (H-1)

# ══════════════════════════════════════════════════════════
# L01 — SKY GRADIENT
# ══════════════════════════════════════════════════════════
print("L01 gradient")
STOPS = [
    (0.00, (0x22, 0xC6, 0xEE)),
    (0.22, (0x12, 0x9C, 0xD6)),
    (0.42, (0x14, 0x74, 0xBC)),
    (0.60, (0x1A, 0x56, 0xA0)),
    (0.74, (0x3D, 0x66, 0xA8)),
    (0.86, (0x9A, 0xA4, 0xC6)),
    (0.94, (0xD9, 0xD2, 0xDE)),
    (1.00, (0xEF, 0xE6, 0xE6)),
]
col = np.zeros((H, W, 3), np.float32)
for i in range(len(STOPS)-1):
    t0, c0 = STOPS[i]; t1, c1 = STOPS[i+1]
    m = (fy >= t0) & (fy <= t1)
    k = ss((fy[m]-t0)/(t1-t0))
    for c in range(3):
        col[..., c][m] = c0[c] + (c1[c]-c0[c])*k

# horizontal warmth: teeal-ish left, indigo right
col[..., 0] += (fx-0.5)*14
col[..., 1] += (fx-0.5)*-4
col[..., 2] += (fx-0.5)*6

base = Image.fromarray(np.clip(col,0,255).astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(3))
save(base, "01_base_gradient.png", "layers3")
comp = base.copy(); save(comp, "01_composite.png", "final3")

# ══════════════════════════════════════════════════════════
# L02 — EDGE HALFTONE (fine, only near edges, tinted)
# ══════════════════════════════════════════════════════════
print("L02 halftone")
S = 3   # supersample factor for anti-aliasing
himg = Image.new("RGBA", (W*S, H*S), (0,0,0,0))
hd = ImageDraw.Draw(himg)
sp = 6.2

def zone_strength(cx, cy):
    """returns (strength, tint) for a dot at pixel coords"""
    u, v = cx/W, cy/H
    left  = ss((0.30 - u)/0.30) if u < 0.30 else 0.0
    left *= 0.22 + 0.78*ss(v/0.80)
    left *= (1.0 - ss((v-0.80)/0.20)*0.35)      # keep going to the bottom
    right = ss((u - 0.70)/0.30) if u > 0.70 else 0.0
    right *= 0.22 + 0.78*ss(v/0.80)
    right *= (1.0 - ss((v-0.80)/0.20)*0.35)
    top   = ss((0.10 - v)/0.10) * 0.18
    s = max(left, right, top)
    if s < 0.03:
        return 0.0, None
    tint = 'warm' if left >= max(right, top) else ('cool' if right >= top else 'white')
    return s, tint

jy = 0
cy = 0.0
while cy < H + sp:
    offset = (sp*0.5) if jy % 2 else 0.0
    cx = offset
    while cx < W + sp:
        s, tint = zone_strength(cx, cy)
        if s > 0.03:
            r = sp * 0.46 * (s**0.62)
            if r >= 0.30:
                a = int(min(120, 150*s))
                if tint == 'warm':
                    c = (255, 236, 216, a)
                elif tint == 'cool':
                    c = (236, 226, 255, a)
                else:
                    c = (255, 255, 255, a)
                hd.ellipse([(cx-r)*S, (cy-r)*S, (cx+r)*S, (cy+r)*S], fill=c)
        cx += sp
    cy += sp*0.87
    jy += 1

dots = himg.resize((W, H), Image.LANCZOS)

# tinted wash beneath the dots (the red / violet colour bleed)
wash_a = np.zeros((H, W), np.float32)
leftm = np.clip((0.38 - fx)/0.38, 0, 1)**1.35 * (0.25 + 0.75*ss(fy/0.85))
rightm = np.clip((fx - 0.62)/0.38, 0, 1)**1.35 * (0.25 + 0.75*ss(fy/0.85))
wash_a = np.clip(leftm*0.55 + rightm*0.55, 0, 0.62)
wr = np.clip(255*leftm + 150*rightm, 0, 255)
wg = np.clip(120*leftm + 70*rightm, 0, 255)
wb = np.clip(80*leftm + 190*rightm, 0, 255)
wash = Image.fromarray(np.dstack([wr, wg, wb, wash_a*255]).astype(np.uint8), "RGBA")
wash = wash.filter(ImageFilter.GaussianBlur(20))

halftone_layer = Image.alpha_composite(wash, dots)
save(halftone_layer, "02_halftone_overlay.png", "layers3")
comp = Image.alpha_composite(comp.convert("RGBA"), halftone_layer).convert("RGB")
save(comp, "02_composite.png", "final3")

# ══════════════════════════════════════════════════════════
# L03 — CLOUD MIST (broad soft bands, no ellipse outlines)
# ══════════════════════════════════════════════════════════
print("L03 mist")
acc = np.zeros((H, W), np.float32)
def puff(cx, cy, rx, ry, s):
    d = np.sqrt(((xx-cx)/rx)**2 + ((yy-cy)/ry)**2)
    return s * np.clip(1-d, 0, 1)**2.0

for p in [
    (160, 150, 420, 90, 0.55), (520, 120, 380, 70, 0.35),
    (900, 165, 400, 80, 0.40), (1150, 420, 380, 110, 0.50),
    (200, 470, 340, 110, 0.40), (620, 380, 300, 90, 0.22),
    (330, 640, 520, 150, 0.45), (980, 640, 480, 160, 0.45),
    (660, 730, 780, 150, 0.50), (1250, 220, 260, 120, 0.35),
]:
    acc += puff(*p)
acc = np.clip(acc, 0, 1)
mist = Image.fromarray((acc*255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(40))

rgba = np.dstack([
    np.full((H, W), 255, np.float32),
    np.full((H, W), 250, np.float32),
    np.full((H, W), 255, np.float32),
    acc*115
]).astype(np.uint8)
cloud_layer = Image.fromarray(rgba, "RGBA")
save(cloud_layer, "03_mist_overlay.png", "layers3")
comp = Image.alpha_composite(comp.convert("RGBA"), cloud_layer).convert("RGB")
save(comp, "03_composite.png", "final3")

# ══════════════════════════════════════════════════════════
# L04 — HEAVENLY BURST  (big diffuse bloom + light rays)
# ══════════════════════════════════════════════════════════
print("L04 burst")
gx, gy = W*0.50, H*0.66
dx = (xx-gx)/(W*0.90); dy = (yy-gy)/(H*1.20)
d  = np.sqrt(dx*dx + dy*dy)

bloom = np.zeros((H, W), np.float32)
for w, s in [(2.10, 0.40), (1.45, 0.28), (0.95, 0.24), (0.60, 0.20), (0.34, 0.16), (0.18, 0.12)]:
    bloom += s * np.clip(1-d/w, 0, 1)**3.0

# broad rising shaft of light
ang = np.abs(xx - gx)/(W*0.5)
shaft = np.clip(1-ang, 0, 1)**2.6
shaft *= np.clip((yy - H*0.10)/(H*0.85), 0, 1)**0.8
shaft *= np.clip(1 - (yy-H*0.55)/(H*0.55), 0.15, 1)
bloom += shaft*0.30

# soft radial rays
theta = np.arctan2(yy-gy, xx-gx)
rays = 0.5 + 0.5*np.cos(theta*9.0)
rays = rays**3.0
rays *= np.clip(1-d/1.25, 0, 1)**2.0
bloom += rays*0.10

bloom = bloom/bloom.max()
rgba = np.dstack([
    np.full((H, W), 255, np.float32),
    np.clip(247 - 14*(1-bloom), 0, 255),
    np.clip(232 - 40*(1-bloom), 0, 255),
    np.clip(bloom**1.05 * 205, 0, 255),
]).astype(np.uint8)
bloom_img = Image.fromarray(rgba, "RGBA").filter(ImageFilter.GaussianBlur(16))
save(bloom_img, "04_burst_overlay.png", "layers3")
comp = Image.alpha_composite(comp.convert("RGBA"), bloom_img).convert("RGB")
save(comp, "04_composite.png", "final3")

# ══════════════════════════════════════════════════════════
# L05 — GRADE (vignette, s-curve, grain)
# ══════════════════════════════════════════════════════════
print("L05 grade")
a = np.array(comp).astype(np.float32)
nx = (xx - W/2)/(W/2); ny2 = (yy - H/2)/(H/2)
vd = np.sqrt(nx*nx*0.50 + ny2*ny2*0.80)
vig = np.clip((vd-0.62)/0.70, 0, 1)**1.7
for c, tint in enumerate((14, 22, 58)):
    a[..., c] = a[..., c]*(1 - vig*0.26) + tint*vig*0.26

x = a/255.0
x = np.where(x < 0.5, 0.5*(2*x)**1.05, 1-0.5*(2*(1-x))**1.05)
a = np.clip(x*255.0, 0, 255)

rng = np.random.default_rng(11)
a = np.clip(a + rng.normal(0, 2.2, (H, W, 1)), 0, 255)

final = Image.fromarray(a.astype(np.uint8), "RGB")
save(final, "05_FINAL_background.png", "final3")
final.save(f"{out}/background_1280x800.png", "PNG")
final.save(f"{out}/background_1280x800.jpg", "JPEG", quality=96, subsampling=0)
os.makedirs("/home/user/memory/renders", exist_ok=True)
final.save("/home/user/memory/renders/heirs_background_1280x800.png", "PNG")
print("DONE", final.size)
