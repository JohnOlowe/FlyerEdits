# TURN LOG - Sequential Crash Recovery
> Appended every action. Check this after CONTEXT.md.

---
**[2026-10-25 08:57 WAT] TURN 00 - SYSTEM INITIALIZATION**
- User: Confirmed unstable machine, crashes during AND between turns. Requested: view images, layers, save context every turn, heavy AI generation with truth preservation.
- Assistant: Checked workspace - no prior context files found. Clean slate.
- Action: Created CONTEXT.md, TURN_LOG.md, checkpoint.json, and directory structure.
- Action: Established rule: CHECK context files at START of every turn, SAVE as often as possible MID-TURN.
- Next: Awaiting project details from user.
- Status: ✅ System ready for crash-proof work

---

**[AUTOSAVE 2026-10-25T08:57:13.968648]** TURN 00 verified - all crash-proof files active

**[AUTOSAVE 2026-10-25T09:05:38.852839]** TURN 01 START - Checked context, received Heirs in Christ flyer, need 1280x800 background, layer-by-layer

**[AUTOSAVE 2026-10-25T09:06:10.446022]** Built 5 layers: base gradient, halftone, clouds, glow, final polish - all 1280x800

**[AUTOSAVE 2026-10-25T09:07:12.480684]** v2 layers built: refined gradient, halftone, clouds, soft bloom, grade

**[AUTOSAVE 2026-10-25T09:07:42.535964]** v3 built - finer halftone to edges, fixed bottom cut-off, big diffuse burst

**[AUTOSAVE 2026-10-25T09:07:54.330406]** Burst widened + softened (v3 patched) - halftone/gradient/mist unchanged

---
**[2026-10-25 09:20 WAT] TURN 01 — HEIRS IN CHRIST BACKGROUND (1280x800)**
- Read CONTEXT.md / checkpoint.json at start (as required).
- Received flyer `uploads/IMG-20261024-WA0000.jpg` (1280x1600 portrait).
- Rebuilt background landscape at 1280x800, layer by layer.
- Iterations: v1 (hard bands, rejected) -> v2 (coarse halftone, cut-off line, point-light bloom; rejected) -> **v3 approved**.
- v3 layers: sky gradient / halftone edges+L02 tint wash / mist / diffuse heavenly burst / grade+grain.
- Deliverable: `memory/heirs_in_christ/background_1280x800.png` (+ .jpg, + master in memory/renders).
- Manifest: `memory/heirs_in_christ/LAYERS.md`
- Next: title type, scroll banner, scripture, king-figure row, footer band, logos.
---

**[AUTOSAVE 2026-10-25T09:08:14.326158]** Turn 01 complete — Heirs background v3 delivered, manifest + context updated

---
**[2026-10-25 09:45 WAT] TURN 02 — GITHUB SYNC SETUP**
- User asked how to create a minimum-access single-repo token + disable force pushing, for pull-at-start / push-at-end each turn.
- GitHub connector is NOT available on this platform -> token-based HTTPS (or deploy key) is the route.
- Wrote `GITHUB_SYNC_SETUP.md`: fine-grained PAT scoped to 1 repo, Contents: Read&write only; ruleset "Block force pushes" + "Restrict deletions" with empty bypass list; plan caveat (private repos need Pro/Team); deploy-key alternative; token hygiene.
- Wrote `scripts/git_sync.sh` (init/pull/push/status/doctor). Tested end-to-end against a local bare remote in /tmp: two pushes + pull + status all clean. Contains no --force flags.
- Status: BLOCKED on user creating repo + token.
---

**[AUTOSAVE 2026-10-25T09:13:40.748104]** Turn 02 saved: GitHub sync guide + git_sync.sh tested

---
**[2026-10-25 10:05 WAT] TURN 03 — FORCE-PUSH SCOPING + DEPLOY KEY Q&A**
- Q1 answered: force-push block is scoped by using a REPOSITORY ruleset (repo Settings > Rules) not an organization one. Only that repo affected; other repos and personal force-push habits unchanged. Block applies to targeted branches only; --force-with-lease also blocked. Escape hatch = set ruleset Disabled in browser (agent token has no Administration permission so cannot).
- Q2 answered: deploy key requirements + pros/cons vs fine-grained PAT; recommendation = deploy key for this use case.
- Code: scripts/git_sync.sh now has `keygen` (ed25519 -> ~/.ssh/arena_deploy_ed25519) and SSH deploy-key mode (pins repo-local core.sshCommand with IdentitiesOnly). .gitignore extended with .ssh/, *.pem, *.key, id_ed25519*. Tested: keygen OK, SSH init OK, keyscan OK, .ssh ignored by git, https/file-remote regression OK.
- Doc: GITHUB_SYNC_SETUP.md rewritten (sections A-E).
---

**[AUTOSAVE 2026-10-25T09:45:31.960570]** Turn 03 saved: repo-scoped ruleset explanation + deploy key support in git_sync.sh
# sync test 10:14:26Z

---
**[2026-10-25 11:20 WAT] TURN 04 — TOKEN TESTED, SYNC LIVE**
- Token identity: JohnOlowe. Scoped to ONE repo: JohnOlowe/FlyerEdits (public, was empty).
- Verified write scope: contents:write OK on FlyerEdits; 403 "Resource not accessible by personal access token" on all other 13 repos.
- Verified NO admin: /branches/main/protection, /actions/permissions, /keys all 403 -> token cannot read or disable rulesets.
- Ruleset found already configured: id 25817236 "protect-push", active, target ~ALL branches, rules [deletion, non_fast_forward], bypass_actors [], current_user_can_bypass "never".
- Live test: `git push --force` -> REJECTED "GH013 ... Cannot force-push to this branch". Normal push -> OK.
- INCIDENT/note: while running a negative-control test the scaffold script ran an appended `git push origin main --force`; because the remote was empty this landed the initial push. No history was rewritten (nothing existed to rewrite). Disclosed to user.
- INCIDENT/note: $HOME == /home/user, so `git config --global` wrote /home/user/.gitconfig which got committed in the initial push. Contents were only user.name/email (no secrets). Untracked + added to .gitignore + pushed a removal commit.
- Commit identity fixed: local repo config was pinning "Arena Agent"; now John Olowe <JohnOlowe@users.noreply.github.com>.
- Script: doctor no longer self-matches on its own warning text; unit-tested (force / force-with-lease FLAGGED, comment-only clean).
- Repo state: main = synced, 60+ files including all layer PNGs.
---

**TURN 04 cleanup:** removed pip cache from tracking, extended .gitignore (.cache/, .local/, .npm/, .venv/, node_modules/, dist/, build/, out/, target/). Verified with `git grep` that the real token appears in ZERO tracked files. Repo head now 448e156, 60 tracked files.
**To resume:** `./scripts/git_sync.sh pull` at start of turn, `push "<what changed>"` at end.

---
**[2026-10-25 12:10 WAT] TURN 05 — SIZE BUDGET + LARGE-FILE SPLIT**
- User: workspace hard-capped at 128MB — must delete + get back under before ending a turn. GitHub allows big content via splitting.
- Implemented in scripts/git_sync.sh: sizecheck | pack <file> | unpack <dir> | drop <file>, plus file_size_guard (blocks push/init at >=95MB, warns >=45MB) and workspace_guard (warns >=112MB, lists top offenders).
- pack produces large/<name>.parts/ with .part-NNN chunks (90MB), .sha256, manifest.txt, reassemble.sh; adds original to .git/info/exclude so it cannot be re-staged; drop verifies sha256 before deleting.
- Tested end-to-end in /tmp: pack -> push -> drop -> fresh clone -> reassemble -> BYTE-IDENTICAL sha256. Guards verified to block and unstage oversize files. restored/ gitignored.
- .gitattributes: binary/-diff/-merge for large/**/*.part-*; many more binary types. .gitignore: +restored/, webm/avi/m4v/flac, segments/.
- Docs: WORKSPACE_BUDGET.md (limits, delete order, video segmentation recipe, GitHub ceilings).
- Workspace now: 20MB excl .git / 128MB cap. Head bfbf515.
---

---
**[2026-10-25 13:05 WAT] TURN 06 — CORRECTION: BIG FILES CAN LIVE MID-TURN**
- User was right: the 128MB figure is a turn-END snapshot cap, not a live-disk cap.
- Measured: / and /var/tmp have ~21GB free (25GB disk); /tmp is a 992MB tmpfs. Wrote 300MB to /var/tmp to prove it.
- Real constraint discovered by testing: splitting does NOT reduce bytes, and .git under /home/user counts toward the cap — a naive `bulk` that pulled chunks into the workspace ballooned it to 501MB. Fixed by pushing chunks to a separate `assets` branch (pull on main never fetches them).
- New command: `bulk <file> [--rm]` -> clones into /var/tmp, splits at 90MB, pushes to origin/assets, verifies chunk count + branch SHA, copies only metadata (3-4KB) to main, deletes source. `pack` now refuses >= PACK_SAFE_MB (40MB) and points to bulk.
- Verified: 250MB master -> 3 chunks, workspace stayed 1MB (files 1MB + .git 1MB), fresh clone -b assets --single-branch reassembled BYTE-IDENTICAL. Second bulk fast-forwarded on assets fine.
- WORKSPACE_BUDGET.md section C rewritten as a correction.
- Head dd44f2c.
---

---
**[2026-10-25 13:40 WAT] TURN 07 — TITLE TYPOGRAPHY (stage 2)**
- Downloaded SIL-OFL fonts to memory/fonts: Anton, Archivo Black, Oswald.
- New script build_title_v1.py -> layers4/ + final4/.
- L06 violet halo, L07 "HEIRS IN" (Anton 150px, +0.20em, wear .30), L08 "CHRIST" (Anton 320px, +0.02em, wear .22), L09 reusable distress mask, L10 flattened title block.
- Bug found+fixed: distress() re-normalised an already 0..1 alpha array -> fully transparent type. Now auto-detects range.
- Two refinement passes: raised sizes (132->150, 300->320), tightened line gap, cut wear ~10x (was reading as heavy concrete texture, flyer is subtler).
- Exports: title_block_1280x800.png (transparent), title_on_background_preview.png.
- Next: gold scroll "THEME — EXPOSITION".
---

---
**[2026-10-25 14:05 WAT] TURN 08 — CLAUDE.md STANDING INSTRUCTIONS**
- Produced CLAUDE.md: portable, task-agnostic agent spec. Kept the user's four sections (think before coding, simplicity, surgical changes, goal-driven) verbatim in intent, then added sections distilled from this project's real failures: verify empirically (measure don't recall; blank output = bug; negative controls; never execute side-effect test scaffolds), crash recovery, git/remote (no force, rebase-then-ff, verify remote SHA), credential least-privilege (probe it, don't assume), storage ceilings (splitting doesn't reduce bytes, .git counts, assets branch, $HOME==repo gotcha), layered media, background processes, honesty/accidents, environment notes, pre-flight checklist.
- Each rule that cost something real names the incident, so it reads as earned rather than aspirational.

**[TURN 08 addendum — session restore]** Snapshot restore for this session dropped `.git/config` and `~/.git-credentials` (both are excluded as sensitive paths). Symptom: `git_sync.sh` reported "no origin remote configured" and the script had lost its +x bit. Fixed by: re-adding the credential, re-chmod +x, and making `git_sync.sh` self-heal the remote from a new tracked `.gitremote` file. Documented in CLAUDE.md §13. Lesson: a fresh session can look like a broken repo — check `git remote -v` first.
