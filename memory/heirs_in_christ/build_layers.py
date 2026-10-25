#!/usr/bin/env python3
"""
Heirs in Christ - 1280x800 Background Builder
Layer by layer reconstruction from flyer
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np
import math

W, H = 1280, 800
out_dir = "/home/user/memory/heirs_in_christ"

def save(img, path):
    img.save(path, "PNG")
    print(f"Saved {path} - {img.size}")

# ========== LAYER 01: BASE SKY GRADIENT ==========
print("Creating Layer 01: Base Gradient...")
# Create vertical + slight horizontal gradient to match flyer
# Top: bright cyan #11BFEF, Mid: #1493C9, Bottom: deeper #1A4A9C with white fade at very bottom
base = Image.new("RGB", (W, H))
pixels = base.load()
# We'll use numpy for smooth gradient
arr = np.zeros((H, W, 3), dtype=np.uint8)
for y in range(H):
    t = y / H  # 0 top, 1 bottom
    # Smooth vertical gradient - match flyer: bright cyan top -> sky blue mid -> soft whitish bottom
    # Use smoothstep interpolation to avoid hard bands
    def lerp(a,b,k): return a + (b-a)*k
    def smoothstep(k): return k*k*(3-2*k)
    if t < 0.55:
        k = smoothstep(t / 0.55)
        # #2CC4EA (44,196,234) -> #1E7ABF (30,122,191) -> #245EA8 (36,94,168)
        r = int(lerp(44, 32, k))
        g = int(lerp(196, 118, k))
        b = int(lerp(234, 185, k))
    else:
        k = smoothstep((t - 0.55) / 0.45)
        # #245EA8 -> #E8EAF2 whitish bottom (232,234,242) with soft transition
        r = int(lerp(32, 232, k))
        g = int(lerp(118, 232, k))
        b = int(lerp(185, 242, k))
    
    # Horizontal subtle shift: left slightly brighter cyan, right slightly deeper blue
    for x in range(W):
        xt = x / W
        # add -15 to +15 shift
        shift = int((xt - 0.5) * 30)  # -15 left, +15 right for blue channel
        rr = max(0, min(255, r + shift//3))
        gg = max(0, min(255, g + shift//4))
        bb = max(0, min(255, b + shift))
        arr[y, x] = (rr, gg, bb)

# Add subtle horizontal vignette of blue
base = Image.fromarray(arr, "RGB")
# Slight blur to smooth
base = base.filter(ImageFilter.GaussianBlur(1.5))

layer01_path = f"{out_dir}/layers/01_base_gradient_1280x800.png"
composite01_path = f"{out_dir}/final/01_composite_base.png"
save(base, layer01_path)
save(base, composite01_path)

# Keep for compositing
composite = base.copy()

# ========== LAYER 02: HALFTONE DOTS ==========
print("Creating Layer 02: Halftone Dots...")
# Halftone is dots pattern with colored gradients at edges
# Create transparent overlay
halftone = Image.new("RGBA", (W, H), (0,0,0,0))
draw = ImageDraw.Draw(halftone)

# Left side: red-orange halftone (from flyer left edge)
# Right side: purple-magenta halftone
# Both with white dots that fade toward center

dot_spacing = 10
for y in range(0, H, dot_spacing):
    for x in range(0, W, dot_spacing):
        # distance from edges
        dist_left = x / W
        dist_right = (W - x) / W
        dist_bottom = y / H
        # left zone: x < 35% width
        left_strength = max(0, 1 - (dist_left*3.3))  # 1 at left edge, 0 after 30%
        left_strength *= (0.4 + 0.6 * (0.3 + 0.7 * dist_bottom))  # stronger at bottom
        # right zone: purple
        right_strength = max(0, 1 - (dist_right*4))  # 1 at right edge, 0 after 25%
        right_strength *= (0.5 + 0.5 * dist_bottom)

        # also top edge subtle dots
        top_strength = 0
        if y < H*0.25:
            # subtle halftone at top
            top_strength = (1 - y/(H*0.25)) * 0.25 * (0.5 + 0.5*math.sin(x*0.02))

        strength = max(left_strength, right_strength, top_strength)
        if strength < 0.08:
            continue

        # dot size varies with strength and adds halftone effect (dots get smaller towards center)
        base_dot = 3.8
        dot_radius = base_dot * strength
        if dot_radius < 0.8:
            continue
        # Add slight random offset for organic feel? Keep grid for authentic halftone
        # Color: left = white dots over red-orange underlay? Actually in flyer halftone is white dots on colored background
        # We'll draw white semi-transparent dots
        alpha = int(180 * strength)
        # Halftone dots are white
        draw.ellipse([x-dot_radius, y-dot_radius, x+dot_radius, y+dot_radius], fill=(255,255,255, alpha))

# Add colored underlay for halftone (subtle gradients at edges behind dots)
halftone_color = Image.new("RGBA", (W, H), (0,0,0,0))
cdraw = ImageDraw.Draw(halftone_color)
# Left red-orange wash
for y in range(H):
    for x in range(int(W*0.38)):
        # distance to left edge and bottom
        xl = 1 - x/(W*0.38)  # 1 at left edge
        yb = y / H
        # create gradient that is strongest at bottom-left
        intensity = xl * (0.3 + 0.7*yb) * 0.55
        if intensity < 0.05:
            continue
        # color: reddish-orange #E85A3A to #D93A2B with fade
        r = int(232)
        g = int(90 + 30*yb)
        b = int(58 + 10*yb)
        a = int(70 * intensity)
        halftone_color.putpixel((x,y), (r,g,b,a))

# Right purple wash
for y in range(H):
    for x in range(int(W*0.62), W):
        xr = (x - W*0.62) / (W*0.38)
        yb = y / H
        intensity = xr * (0.3 + 0.7*yb) * 0.50
        if intensity < 0.05:
            continue
        r = int(140 + 20*xr)
        g = int(60 + 20*yb)
        b = int(160 + 30*xr)
        a = int(60 * intensity)
        halftone_color.putpixel((x,y), (r,g,b,a))

halftone_color = halftone_color.filter(ImageFilter.GaussianBlur(12))

# Composite halftone color under dots
halftone_combined = Image.alpha_composite(halftone_color, halftone)
halftone_combined_path = f"{out_dir}/layers/02_halftone_overlay.png"
save(halftone_combined, halftone_combined_path)

# Composite onto base
composite = Image.alpha_composite(composite.convert("RGBA"), halftone_combined).convert("RGB")
composite02_path = f"{out_dir}/final/02_composite_halftone.png"
save(composite, composite02_path)
print("Layer 02 done")

# ========== LAYER 03: SOFT CLOUDS ==========
print("Creating Layer 03: Clouds...")
clouds = Image.new("RGBA", (W, H), (0,0,0,0))
cdraw = ImageDraw.Draw(clouds)

# Create soft cloud blobs using large blurred ellipses
# We mimic flyer: clouds at top-mid and bottom-right area
def soft_cloud(cx, cy, w, h, opacity=90):
    # draw multiple overlapping ellipses with blur
    cloud_blob = Image.new("RGBA", (W, H), (0,0,0,0))
    bdraw = ImageDraw.Draw(cloud_blob)
    # main ellipse
    bdraw.ellipse([cx-w//2, cy-h//2, cx+w//2, cy+h//2], fill=(255,255,255, opacity))
    # Add puff details
    for ox, oy, ow, oh, op in [
        (-w*0.25, -h*0.15, w*0.6, h*0.7, opacity*0.8),
        (w*0.20, -h*0.10, w*0.55, h*0.65, opacity*0.75),
        (-w*0.10, h*0.15, w*0.7, h*0.5, opacity*0.6),
        (w*0.10, h*0.08, w*0.5, h*0.45, opacity*0.5),
    ]:
        bdraw.ellipse([cx+ox-ow//2, cy+oy-oh//2, cx+ox+ow//2, cy+oy+oh//2], fill=(255,255,255, int(op)))
    # blur heavily for softness
    cloud_blob = cloud_blob.filter(ImageFilter.GaussianBlur(18))
    return cloud_blob

# Define cloud positions (adapted to landscape)
cloud_definitions = [
    # Top small whispy clouds
    (180, 140, 420, 110, 55),
    (780, 180, 380, 100, 50),
    (1020, 420, 480, 130, 65),  # right mid cloud from flyer
    (640, 200, 300, 80, 40),
    # Larger bottom clouds that create hazy base
    (250, 620, 600, 180, 70),
    (950, 580, 500, 160, 60),
    (640, 680, 800, 140, 45),  # bottom mist
]

clouds_combined = Image.new("RGBA", (W, H), (0,0,0,0))
for cx, cy, w, h, op in cloud_definitions:
    blob = soft_cloud(cx, cy, w, h, op)
    clouds_combined = Image.alpha_composite(clouds_combined, blob)

clouds_path = f"{out_dir}/layers/03_clouds_overlay.png"
save(clouds_combined, clouds_path)

composite = Image.alpha_composite(composite.convert("RGBA"), clouds_combined).convert("RGB")
composite03_path = f"{out_dir}/final/03_composite_clouds.png"
save(composite, composite03_path)
print("Layer 03 done")

# ========== LAYER 04: CENTRAL HEAVENLY GLOW ==========
print("Creating Layer 04: Central Glow...")
glow = Image.new("RGBA", (W, H), (0,0,0,0))
# Create radial glow centered at where figures were: center, slightly low (640, 520)
# In flyer it's bright white-yellow burst behind figures
glow_arr = np.zeros((H, W, 4), dtype=np.uint8)
cx, cy = 640, 520
max_dist = 700

for y in range(H):
    for x in range(W):
        dx = x - cx
        dy = y - cy
        # elliptical shape: wider horizontally
        dy_scaled = dy * 1.1
        dist = math.sqrt(dx*dx + dy_scaled*dy_scaled)
        t = dist / max_dist  # 0 center, 1 edge
        if t > 1:
            continue
        # Glow intensity: inverse distance with falloff
        # Strongest at center, warm white
        if t < 0.25:
            intensity = 0.95 - t*0.8
            r, g, b = 255, 250, 225
            a = int(210 * intensity)
        elif t < 0.50:
            intensity = 0.75 - (t-0.25)*1.2
            r, g, b = 255, 248, 235
            a = int(180 * intensity)
        elif t < 0.75:
            intensity = 0.45 - (t-0.5)*1.0
            r, g, b = 255, 255, 245
            a = int(120 * intensity)
        else:
            intensity = 0.20 - (t-0.75)*0.8
            r, g, b = 255, 255, 255
            a = int(60 * intensity)
        if a <= 0:
            continue
        # Blend with existing: lighter
        glow_arr[y, x] = (r, g, b, a)

glow = Image.fromarray(glow_arr, "RGBA")
glow = glow.filter(ImageFilter.GaussianBlur(22))

# Add extra bright core
core = Image.new("RGBA", (W, H), (0,0,0,0))
core_draw = ImageDraw.Draw(core)
# Brightest spot
core_draw.ellipse([cx-180, cy-140, cx+180, cy+140], fill=(255,255,255, 95))
core = core.filter(ImageFilter.GaussianBlur(35))
glow = Image.alpha_composite(glow, core)

glow_path = f"{out_dir}/layers/04_center_glow_overlay.png"
save(glow, glow_path)

composite = Image.alpha_composite(composite.convert("RGBA"), glow).convert("RGB")
# Soften composite slightly
composite = composite.filter(ImageFilter.GaussianBlur(0.3))
composite04_path = f"{out_dir}/final/04_composite_glow.png"
save(composite, composite04_path)
print("Layer 04 done")

# ========== LAYER 05: FINAL POLISH (VIGNETTE + SHARPEN) ==========
print("Creating Layer 05: Final Polish...")
final = composite.copy()
# Add subtle vignette to focus center and give depth for projector
vignette = Image.new("RGBA", (W, H), (0,0,0,0))
varr = np.zeros((H, W, 4), dtype=np.uint8)
for y in range(H):
    for x in range(W):
        # distance from center
        nx = (x - W/2) / (W/2)
        ny = (y - H/2) / (H/2)
        dist = math.sqrt(nx*nx*0.7 + ny*ny)  # elliptical
        vignette_strength = max(0, (dist - 0.65) * 0.35)
        if vignette_strength > 0:
            a = int(35 * vignette_strength)
            varr[y, x] = (10, 20, 60, a)  # subtle blue vignette
glow_vignette = Image.fromarray(varr, "RGBA")
glow_vignette = glow_vignette.filter(ImageFilter.GaussianBlur(20))

final = Image.alpha_composite(final.convert("RGBA"), glow_vignette).convert("RGB")

final_path = f"{out_dir}/final/05_FINAL_BACKGROUND_1280x800.png"
save(final, final_path)

# Also save a copy to memory/renders for easy access
final.save("/home/user/memory/renders/heirs_background_final_1280x800.png", "PNG")
final.save("/home/user/memory/heirs_in_christ/final_background_1280x800.jpg", "JPEG", quality=95)

print(f"\n✅ All layers complete!")
print(f"Base: {W}x{H}")
print(f"Final: {final_path}")
