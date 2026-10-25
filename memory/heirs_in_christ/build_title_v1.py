#!/usr/bin/env python3
"""
Heirs in Christ — TITLE TYPOGRAPHY, layer by layer
L06 title shadow / glow
L07 "HEIRS IN"
L08 "CHRIST"
L09 grunge distress mask (exported so it is reusable/tweakable)

Canvas: 1280x800. Every layer is a transparent PNG. A composite snapshot
is written after each layer so any stage can be revisited.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import numpy as np, os, math

W, H = 1280, 800
ROOT = "/home/user/memory/heirs_in_christ"
FONTS = "/home/user/memory/fonts"
L = f"{ROOT}/layers4"; C = f"{ROOT}/final4"
os.makedirs(L, exist_ok=True); os.makedirs(C, exist_ok=True)
SS = 2  # supersample factor

# palette sampled from the flyer
INK_TOP    = (0x50, 0x43, 0xB2)
INK_BOT    = (0x24, 0x1F, 0x66)
INK_EDGE   = (0x1E, 0x1B, 0x52)
GLOW       = (0x6A, 0x5A, 0xD6)

def save(img, name, folder=L):
    p = f"{folder}/{name}"; img.save(p, "PNG"); print("  saved", os.path.basename(p))
    return p

# ─────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────
def render_line(text, font_path, size, tracking=0.0, shear=-6.0):
    """Render one line to an RGBA image cropped to the ink. shear in degrees (italic)."""
    font = ImageFont.truetype(font_path, size * SS)
    # measure with tracking
    widths, adv = [], []
    for ch in text:
        bb = font.getbbox(ch)
        adv.append(font.getlength(ch))
        widths.append(bb)
    tr = tracking * size * SS
    total = sum(adv) + tr * (len(text) - 1)
    asc, desc = font.getmetrics()
    pad = size * SS // 2
    im = Image.new("L", (int(total) + pad * 2, asc + desc + pad * 2), 0)
    d = ImageDraw.Draw(im)
    x = pad
    for ch in text:
        d.text((x, pad), ch, font=font, fill=255)
        x += font.getlength(ch) + tr
    im = im.crop(im.getbbox())

    if shear:
        w, h = im.size
        shift = int(math.tan(math.radians(shear)) * h)
        im = im.transform((w + abs(shift), h), Image.AFFINE,
                          (1, shift / h if shift else 0, 0 if shift > 0 else -shift,
                           0, 1, 0), resample=Image.BICUBIC)
    im = im.resize((im.width // SS, im.height // SS), Image.LANCZOS)
    return im


def noise_field(w, h, seed=0, octaves=((4, 0.55), (12, 0.30), (34, 0.15))):
    """Smooth multi-octave value noise in 0..1"""
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    for cells, weight in octaves:
        small = rng.random((max(2, h // cells), max(2, w // cells))).astype(np.float32)
        layer = np.array(Image.fromarray((small * 255).astype(np.uint8))
                         .resize((w, h), Image.BICUBIC), np.float32) / 255.0
        acc += weight * layer
    acc -= acc.min(); acc /= max(1e-6, acc.max())
    return acc


def gradient_fill(size, top, bot, slant=0.0):
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = yy / max(1, h - 1)
    if slant:
        t = np.clip(t + (xx / max(1, w - 1) - 0.5) * slant, 0, 1)
    out = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        out[..., c] = top[c] + (bot[c] - top[c]) * t
    return out


def distress(alpha, seed, strength=1.0):
    """Erode the ink edge irregularly + punch speckle holes, like worn print."""
    h, w = alpha.shape
    a = alpha.astype(np.float32)
    if a.max() > 1.5:          # accept either 0..255 or 0..1 input
        a = a / 255.0
    ink = (a > 0.02)                                # hard limit: never invent ink outside
    n1 = noise_field(w, h, seed)                    # broad blotches
    n2 = noise_field(w, h, seed + 7,
                     ((1, 0.45), (3, 0.33), (7, 0.22)))  # very fine grain

    # eat the edges: subtract noise, rescale — but keep it inside the glyphs
    a = np.clip((a - (n1 - 0.5) * 0.32 * strength) * 1.9, 0, 1)
    a = np.where(ink, a, 0.0)
    # fine stipple: sparse holes inside the ink
    holes = (n2 > 0.78) & (a > 0.35)
    a = np.where(holes, a * (0.45 + 0.35 * strength), a)
    # soften the result a touch so it doesn't look aliased
    img = Image.fromarray((a * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.6))
    return np.array(img, np.float32) / 255.0


def make_text_layer(text, font_path, size, tracking, y_center, seed,
                    shear=-6.0, distress_strength=1.0):
    mask = render_line(text, font_path, size, tracking, shear)
    w, h = mask.size
    # position
    x = (W - w) // 2
    y = int(y_center - h / 2)
    canvas = Image.new("L", (W, H), 0)
    canvas.paste(mask, (x, y))

    a = np.array(canvas, np.float32) / 255.0
    a = distress(a, seed, distress_strength)
    inset = np.zeros((H, W), np.float32)
    inset[y:y + h, x:x + w] = 1.0  # only where the line actually is

    # colour: vertical gradient + faint light from upper-left
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = np.clip((yy - y) / max(1, h), 0, 1)
    grad = np.zeros((H, W, 3), np.float32)
    for c in range(3):
        grad[..., c] = INK_TOP[c] + (INK_BOT[c] - INK_TOP[c]) * t
    # subtle top-left lighting
    light = 0.10 * np.clip(1 - ((xx - x) / max(1, w)), 0, 1) * (1 - t)
    grad = np.clip(grad + light[..., None] * 90, 0, 255)

    rgba = np.dstack([grad, a * 255]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA"), a


# ─────────────────────────────────────────────────────────────
# L06 — shadow / glow behind the type
# ─────────────────────────────────────────────────────────────
print("L06 shadow/glow")
heirs = render_line("HEIRS IN", f"{FONTS}/Anton-Regular.ttf", 150, tracking=0.20, shear=-6)
christ = render_line("CHRIST",  f"{FONTS}/Anton-Regular.ttf", 320, tracking=0.02, shear=-6)
print("   HEIRS IN box:", heirs.size, " CHRIST box:", christ.size)

Y_HEIRS = 208   # centre of the top line
Y_CHRIST = 432  # centre of the big line

shadow_mask = Image.new("L", (W, H), 0)
shadow_mask.paste(heirs, ((W - heirs.width) // 2, Y_HEIRS - heirs.height // 2))
shadow_mask.paste(christ, ((W - christ.width) // 2, Y_CHRIST - christ.height // 2))

glow = shadow_mask.filter(ImageFilter.GaussianBlur(26))
glow_arr = np.array(glow, np.float32) / 255.0
glow_arr = np.clip(glow_arr * 1.5, 0, 1)
rgba = np.dstack([
    np.full((H, W), GLOW[0], np.float32),
    np.full((H, W), GLOW[1], np.float32),
    np.full((H, W), GLOW[2], np.float32),
    glow_arr * 105,
]).astype(np.uint8)
l06 = Image.fromarray(rgba, "RGBA")
save(l06, "06_title_glow.png")

base = Image.open(f"{ROOT}/final3/05_FINAL_background.png").convert("RGBA")
comp = Image.alpha_composite(base, l06)
save(comp, "06_composite.png", C)

# ─────────────────────────────────────────────────────────────
# L07 / L08 — the two type lines
# ─────────────────────────────────────────────────────────────
print("L07 HEIRS IN")
l07, a07 = make_text_layer("HEIRS IN", f"{FONTS}/Anton-Regular.ttf", 150,
                           tracking=0.20, y_center=Y_HEIRS, seed=11,
                           distress_strength=0.30)
save(l07, "07_heirs_in.png")
comp = Image.alpha_composite(comp, l07)
save(comp, "07_composite.png", C)

print("L08 CHRIST")
l08, a08 = make_text_layer("CHRIST", f"{FONTS}/Anton-Regular.ttf", 320,
                           tracking=0.02, y_center=Y_CHRIST, seed=29,
                           distress_strength=0.22)
save(l08, "08_christ.png")
comp = Image.alpha_composite(comp, l08)
save(comp, "08_composite.png", C)

# ─────────────────────────────────────────────────────────────
# L09 — the distress mask, exported on its own (white = ink survives)
# ─────────────────────────────────────────────────────────────
print("L09 distress mask")
dm = np.clip((a07 + a08), 0, 1)
mask_img = Image.fromarray((dm * 255).astype(np.uint8), "L").convert("RGBA")
save(mask_img, "09_distress_mask.png")

# ─────────────────────────────────────────────────────────────
# convenience: the finished title block, transparent, both lines
# ─────────────────────────────────────────────────────────────
title_block = Image.new("RGBA", (W, H), (0, 0, 0, 0))
title_block = Image.alpha_composite(title_block, l06)
title_block = Image.alpha_composite(title_block, l07)
title_block = Image.alpha_composite(title_block, l08)
save(title_block, "10_TITLE_BLOCK.png")
title_block.save(f"{ROOT}/title_block_1280x800.png", "PNG")

comp = Image.alpha_composite(comp, l06)  # glow sits behind in reality; keep visual same
comp.save(f"{ROOT}/title_on_background_preview.png", "PNG")
print("\ndone")
