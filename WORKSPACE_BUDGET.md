# Size budget & large-file playbook

Two different limits, two different strategies.

| | Limit | Strategy |
|---|---|---|
| **Workspace** (`/home/user`) | **128 MB** total, snapshotted each turn | stay lean — delete intermediates *before* the turn ends |
| **GitHub** | **100 MB per file** (hard reject), repo ideally < 1 GB | `split` big files into ≤ 90 MB chunks, commit the chunks |

---

## A. Workspace: the 128 MB rule

Anything over ~128 MB in the workspace is not captured in the turn snapshot. So a file that
big **dies with a crash**, which is worse than not having it.

Rule I follow every turn:
1. `./scripts/git_sync.sh sizecheck` — mid-turn and again before the turn ends
2. Keep workspace (excluding `.git`) under **112 MB** (the soft line the script warns at)
3. If a step pushes past that: **delete the intermediate, push what matters, then finish the turn**

What gets deleted first (all safe — they're already in git and on GitHub):

| Priority | What | Why it's safe |
|---|---|---|
| 1 | `segments/`, `raw_video/`, `*.mov`, `*.webm` scratch | gitignored; masters live elsewhere |
| 2 | rejected drafts (`final/`, `final2/`, `archive/`) | already committed; `git checkout` brings them back |
| 3 | `restored/` reassembled files | regenerate with `./scripts/git_sync.sh unpack <dir>` |
| 4 | composite snapshots after each layer | the layer PNGs + build script are the source of truth |
| never | `CONTEXT.md`, `TURN_LOG.md`, `checkpoint.json`, `scripts/` | that's the memory — a few KB |

## B. GitHub: files over 100 MB

GitHub **rejects any single file ≥ 100 MB** on push, and warns at 50 MB. Splitting works
because the cap is per *file*, not per commit.

```bash
# small-ish files (< 40 MB): chunks stay on main
./scripts/git_sync.sh pack clip.mp4
./scripts/git_sync.sh push "add clip chunks"
./scripts/git_sync.sh drop clip.mp4

# anything bigger: chunks go to the 'assets' branch, workspace never sees them
./scripts/git_sync.sh bulk /var/tmp/master.mov --rm
```

What `pack` produces in `large/<name>.parts/`:

```
big_render.mp4.part-000     ← 90 MB chunks
big_render.mp4.part-001
…
big_render.mp4.sha256       ← integrity record
manifest.txt                ← bytes, chunks, chunk size, timestamp
reassemble.sh               ← one-command restore + hash verify
```

Restore anywhere, even after a crash:

```bash
git clone https://github.com/JohnOlowe/FlyerEdits.git
cd FlyerEdits
bash large/big_render.mp4.parts/reassemble.sh
# ✔ restored restored/big_render.mp4 (sha256 ok)
```

Verified working: a 6 MB test file split into chunks, committed, deleted locally, cloned
fresh, reassembled → **byte-identical sha256**.

### Automatic guards
- `push` and `init` run a **file-size guard**: any staged file ≥ 95 MB → the whole push is
  refused, everything is unstaged, and you get the exact `pack` command to run.
- 45–95 MB → allowed, with a warning.
- `pack` adds the un-split original to `.git/info/exclude` (local-only) so `git add -A`
  can't re-stage it before you `drop` it.
- `push` also runs the **workspace guard**: warns above 112 MB and lists the top offenders.

### Tuning
```bash
MAX_FILE_MB=95 WARN_FILE_MB=45 CHUNK_MB=90 ./scripts/git_sync.sh push "…"
```

## C. Correction: big files CAN live here during a turn

The 128 MB is a **snapshot** cap, not a disk cap. Measured on this machine:

| Location | Size | Snapshotted? |
|---|---|---|
| `/` (and `/home/user`) | 25 GB, ~21 GB free | `/home/user` yes |
| `/tmp` (tmpfs, RAM-backed) | 992 MB | no |
| `/var/tmp` | same 25 GB disk | no |

So a 500 MB master **can** sit here mid-turn — you just have to get rid of it before the
turn ends. Verified: a 250 MB file was created, split, pushed and deleted inside one turn.

**But splitting does not reduce total bytes.** 500 MB of chunks is still 500 MB, and
`.git` inside `/home/user` counts toward the cap too — so committing chunks to `main` makes
the workspace *worse* (source + chunks + pack objects). That's why the flow is:

```bash
./scripts/git_sync.sh bulk /var/tmp/master.mov --rm
```

`bulk` does the whole job in scratch space outside the workspace:

1. clones the repo into `/var/tmp` (never `/home/user`)
2. splits the file into 90 MB chunks there
3. pushes them to a **separate `assets` branch**
4. verifies the chunk count + branch SHA against the remote
5. deletes the source (`--rm`) and the scratch clone
6. commits only **metadata** (manifest + sha256 + reassemble.sh, a few KB) to `main`

Measured on a real run: 250 MB master → 3 chunks, **workspace total 1 MB**, verified
byte-identical after re-cloning from scratch.

Why a separate branch: `pull` on `main` fetches only `main`'s objects, so the big blobs
never enter the workspace. Restore with
`git clone -b assets --single-branch <url>`.

### When to use which

| | `pack` | `bulk` |
|---|---|---|
| used for | files < 40 MB | anything bigger |
| where chunks are committed | `main` | `assets` branch |
| workspace/.git growth | yes, by the file's size | **none** |
| guard | refuses ≥ `PACK_SAFE_MB` (40 MB) | no limit |

### Still worth doing for video
- Trim/transcode before importing when you can — a 2 GB master is 2 GB of transfer either way
- Export in segments so each piece is already chunk-sized:
  `ffmpeg -i in.mp4 -c copy -f segment -segment_time 60 -reset_timestamps 1 segments/part-%03d.mp4`
- Keep true masters on Drive; commit the **chunked deliverable** + layer PNGs + build scripts

`segments/` is gitignored; `large/` is committed (on whichever branch).

## D. Other GitHub ceilings to keep in mind
- 100 MB / file — hard reject (hence the 90 MB chunks)
- 50 MB / file — warning
- ~1 GB repo — recommended ceiling; 5 GB is the practical hard wall
- Git LFS — 1 GB free storage, metered bandwidth; **not** needed for this workflow
- Force-push is blocked by the `protect-push` ruleset, so **anything pushed is permanent** —
  check before you `pack` something huge that you'll regret
