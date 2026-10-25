# FlyerEdits — "Heirs in Christ" projector graphics

Working repository for the Foursquare Students' Fellowship (UI) Sunday Service visuals.
Target format: **1280×800** projector slides.

Everything here is built **layer by layer** — each layer is a standalone PNG, and every
stage has a flattened composite snapshot so any point in the build can be revisited.

## Layout

```
CONTEXT.md            crash-proof memory — read this first
TURN_LOG.md           append-only log of every turn
checkpoint.json       machine-readable state (layers, renders, next steps)
WORKSPACE_BUDGET.md   size rules + large-file (split) workflow
GITHUB_SYNC_SETUP.md  how the token/ruleset for this repo are scoped

uploads/              original user-supplied references (never modified)
memory/
  autosaves/          mid-turn autosave snapshots
  renders/            master exports
  heirs_in_christ/
    source/           original flyer
    build_layers.py       v1 (superseded)
    build_layers_v2.py    v2 (superseded)
    build_layers_v3.py    CURRENT build script
    layers/            v1 layers        (rejected)
    final/             v1 composites    (rejected)
    layers2/           v2 layers        (rejected)
    final2/            v2 composites    (rejected)
    layers3/           v3 layers        ← CURRENT
    final3/            v3 composites + FINAL background
    LAYERS.md          layer manifest
scripts/
  git_sync.sh         pull/push/pack/bulk/sizecheck helper
  save_checkpoint.py  autosave helper
```

## Current deliverable

`memory/heirs_in_christ/background_1280x800.png` — clean 1280×800 background with no
type and no figures, built from five layers:

| # | Layer | File |
|---|---|---|
| L01 | sky gradient | `layers3/01_base_gradient.png` |
| L02 | halftone + tint wash | `layers3/02_halftone_overlay.png` |
| L03 | mist / clouds | `layers3/03_mist_overlay.png` |
| L04 | heavenly burst | `layers3/04_burst_overlay.png` |
| L05 | grade (vignette, S-curve, grain) | `final3/05_FINAL_background.png` |

Rebuild everything:

```bash
pip install pillow numpy
python3 memory/heirs_in_christ/build_layers_v3.py
```

## Sizes

~19 MB of assets across 61 files; the packed repo is ~14 MiB. No file is near GitHub's
100 MB per-file limit. Anything large goes through `scripts/git_sync.sh bulk`, which
splits it into ≤90 MB chunks on a separate `assets` branch so a `main` clone stays small.

## House rules

- `main` is protected by a ruleset: **force-push and branch deletion are blocked**, no bypass list.
- The automation token has **Contents: read/write on this repo only** — no admin, no other repos.
- Never commit `.git-credentials`, `.ssh/`, `*.pem`, raw video masters, or build caches.
