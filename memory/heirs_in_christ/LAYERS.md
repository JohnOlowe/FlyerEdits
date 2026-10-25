# LAYERS MANIFEST — Heirs in Christ (1280×800 projector background)

**Source reference:** `uploads/IMG-20261024-WA0000.jpg` (flyer, 1280×1600 portrait)
**Target:** projector slide background, 1280×800 landscape
**Method:** rebuilt from scratch, layer by layer, each layer saved as standalone PNG (transparent where applicable) + a flattened composite snapshot so you can roll back to any stage.

## Current approved build: `v3` (`final3/`)

| # | Layer file (standalone) | Blended / composited file | What it is |
|---|---|---|---|
| 01 | `layers3/01_base_gradient.png` | `final3/01_composite.png` | Sky gradient — cyan `#22C6EE` top → sky blue → deep `#1A56A0` → navy → pale lavender-white bottom. Horizontal teal→indigo shift. |
| 02 | `layers3/02_halftone_overlay.png` | `final3/02_composite.png` | Print-dot halftone, fine 6.2px grid, fades out by ~30% from each side. Warm red-orange tint left, violet tint right, faint white at top. |
| 03 | `layers3/03_mist_overlay.png` | `final3/03_composite.png` | Cloud / mist bands — broad soft ramps, no visible ellipse edges. Luminous white-blue, ~45% opacity. |
| 04 | `layers3/04_burst_overlay.png` | `final3/04_composite.png` | Heavenly burst — 6-octave diffuse bloom centred (640, 528), rising light shaft, faint radial rays. Warm white-yellow. |
| 05 | — | `final3/05_FINAL_background.png` | Grade — elliptical vignette, gentle S-curve contrast, 2.2σ grain (kills projector banding). **← DELIVERABLE** |

## Exports
- `memory/heirs_in_christ/background_1280x800.png` — lossless PNG
- `memory/heirs_in_christ/background_1280x800.jpg` — q96, 4:4:4
- `memory/renders/heirs_background_1280x800.png` — master copy

## Rejected earlier drafts (kept for reference)
- `final/` — v1: hard gradient bands, visible seams
- `final2/` — v2: halftone too coarse, hard cut-off line at 87% height, bloom read as a point light

## Build scripts
- `build_layers_v3.py` — **current**, run this to regenerate everything
- `build_layers_v2.py`, `build_layers.py` — earlier drafts

## To re-run
```bash
pip install pillow numpy -q
python3 memory/heirs_in_christ/build_layers_v3.py
```

## Layer order (bottom → top)
1. base gradient
2. halftone (dots + tint wash)
3. mist
4. burst
5. grade (vignette + grain)


---

# STAGE 2 — TITLE TYPOGRAPHY (`layers4/`, `final4/`)

Canvas 1280×800. Font: **Anton** (SIL OFL, `memory/fonts/Anton-Regular.ttf`),
rendered at 2× and downsampled. Slight italic shear −6°.

| # | Layer file | Composite snapshot | What it is |
|---|---|---|---|
| L06 | `layers4/06_title_glow.png` | `final4/06_composite.png` | soft violet halo (#6A5AD6) behind the type, 26px blur |
| L07 | `layers4/07_heirs_in.png` | `final4/07_composite.png` | "HEIRS IN" — Anton 150px, tracking +0.20em, light wear |
| L08 | `layers4/08_christ.png` | `final4/08_composite.png` | "CHRIST" — Anton 320px, tracking +0.02em, gradient ink |
| L09 | `layers4/09_distress_mask.png` | — | the wear mask on its own (white = ink survives), reusable |
| — | `layers4/10_TITLE_BLOCK.png` | `final4/08_composite.png` | glow + both lines flattened, fully transparent bg |

**Exports**
- `title_block_1280x800.png` — the title alone, transparent (stack this on anything)
- `title_on_background_preview.png` — title over the approved background

**Measurements**
- "HEIRS IN" ink box: 667 × 132 @ centre y=208
- "CHRIST" ink box: 858 × 280 @ centre y=432
- gap between lines ≈ 36 px; whole block spans y≈142…575

**Ink colour:** gradient `#5043B2` → `#241F66` top-to-bottom, +10% upper-left light
**Wear:** multi-octave noise edge erosion (0.32) + fine speckle holes (0.22–0.30)

**Rebuild:** `python3 memory/heirs_in_christ/build_title_v1.py`

**Note:** first run produced invisible type — `distress()` normalised an already-normalised
0..1 array a second time, which zeroed every pixel. Fixed by auto-detecting the input range.
