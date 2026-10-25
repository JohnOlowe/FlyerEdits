# 🎬 PROJECT CONTEXT — CRASH-PROOF MEMORY
> CHECKED AT START OF EVERY TURN, UPDATED MID-TURN.
> Last Updated: 2026-10-25 09:20 WAT (Africa/Lagos) — Turn 01

## CURRENT PROJECT
- **Name:** Heirs in Christ — Sunday Service (Foursquare Students' Fellowship, UI)
- **Source:** `uploads/IMG-20261024-WA0000.jpg` (flyer, 1280×1600 portrait)
- **Target:** projector visuals, **1280×800 landscape**
- **Status:** Stage 1 DONE — background rebuilt layer-by-layer (v3 approved)

## WORKFLOW RULES (LOCKED)
1. Read `CONTEXT.md` + `TURN_LOG.md` + `checkpoint.json` at START of every turn
2. Save after every file/decision (mid-turn autosave via `scripts/save_checkpoint.py "msg"`)
3. Full summary at END of turn
4. Every layer = its own transparent PNG + dedicated build script
5. Log what must stay TRUE vs what is AI-generated

## PROJECT STRUCTURE
```
/home/user/
├── CONTEXT.md  TURN_LOG.md  checkpoint.json
├── uploads/                          <- user uploads (never modify)
├── memory/
│   ├── assets/  layers/  renders/  autosaves/
│   └── heirs_in_christ/
│       ├── source/original_flyer.jpg
│       ├── build_layers_v3.py        <- CURRENT build script
│       ├── layers3/                  <- standalone layer PNGs (v3)
│       ├── final3/                   <- composite after each layer + FINAL
│       ├── final/ final2/            <- rejected drafts (v1, v2)
│       ├── LAYERS.md                 <- layer manifest
│       └── background_1280x800.png/.jpg
└── scripts/save_checkpoint.py
```

## LAYER REGISTRY (1280×800, bottom → top)
| # | Layer | File | Notes |
|---|-------|------|-------|
| L01 | Sky gradient | `layers3/01_base_gradient.png` | cyan #22C6EE → #1A56A0 → pale lavender bottom |
| L02 | Halftone | `layers3/02_halftone_overlay.png` | 6.2px dot grid, 30% side fade, warm L / violet R |
| L03 | Mist/clouds | `layers3/03_mist_overlay.png` | broad soft bands, no hard ellipse edges |
| L04 | Heavenly burst | `layers3/04_burst_overlay.png` | 6-octave diffuse bloom @ (640,528) + shaft + rays |
| L05 | Grade | `final3/05_FINAL_background.png` | vignette + S-curve + 2.2σ grain |

**DELIVERABLE:** `memory/heirs_in_christ/background_1280x800.png` (+ .jpg, master in `memory/renders/`)

## GENERATION LOG
| Turn | Action | Output |
|------|--------|--------|
| 01 | Rebuilt flyer background at 1280×800, 3 drafts (v1/v2 rejected, v3 approved) | background_1280x800.png |

## MUST STAY TRUE (from original flyer)
- Brand: Foursquare Students' Fellowship, UI — logos top centre
- Text: "SUNDAY SERVICE", "HEIRS IN CHRIST", "THEME EXPOSITION" scroll, Romans 8:16–17
- Ministering: Adelaja Timilehin
- 8:30AM, SUNDAY, 25TH OCTOBER 2026
- BELLO DOME, SULTAN BELLO HALL, UNIVERSITY OF IBADAN
- Colour language: cyan/blue sky, warm-red left halftone, violet right halftone, gold scroll

## NEXT STEPS
1. Await approval / tweaks on background
2. Build remaining layers as separate transparent PNGs:
   - title typography "HEIRS IN CHRIST" (purple, distressed)
   - gold scroll banner "THEME — EXPOSITION"
   - scripture line Romans 8:16–17
   - crown/king figure row (AI-generated, keep style consistent)
   - footer navy band + service details
   - Foursquare logos strip
3. Assemble final 1280×800 slide

## RECOVERY
1. Read this file → 2. `TURN_LOG.md` → 3. `checkpoint.json` → 4. `memory/autosaves/` → 5. resume NEXT STEPS
