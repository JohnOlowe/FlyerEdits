#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# git_sync.sh — crash-safe pull/push for the graphics workspace
# Never uses --force. Ever.
#
#   ./scripts/git_sync.sh init <remote-url> [branch]
#   ./scripts/git_sync.sh pull          # START of turn
#   ./scripts/git_sync.sh push "msg"    # END of turn
#   ./scripts/git_sync.sh status
#   ./scripts/git_sync.sh doctor
#
#   Large files (GitHub caps a single file at 100 MB):
#   ./scripts/git_sync.sh pack <file>      # split into <=90 MB chunks under large/
#   ./scripts/git_sync.sh unpack <file>    # reassemble + verify sha256
#   ./scripts/git_sync.sh drop <file>      # delete local copy once packed
#   ./scripts/git_sync.sh sizecheck        # workspace vs 128 MB, repo vs limits
#
#   Anything bigger than the workspace cap (raw masters, big renders):
#   ./scripts/git_sync.sh bulk <file> [--rm]   # split + push from scratch space,
#                                              # never touching /home/user
#
#   Deploy-key (SSH) mode:
#   ./scripts/git_sync.sh keygen           # make an ed25519 keypair, print pubkey
#   ./scripts/git_sync.sh init git@github.com:<you>/<repo>.git
# ─────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/user}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/arena_deploy_ed25519}"

# GitHub rejects any single file >= 100 MB; we split before that.
MAX_FILE_MB="${MAX_FILE_MB:-95}"    # hard stop at push time
WARN_FILE_MB="${WARN_FILE_MB:-45}"  # soft warning
CHUNK_MB="${CHUNK_MB:-90}"          # split size
WORKSPACE_MB="${WORKSPACE_MB:-128}" # sandbox cap
WORKSPACE_SOFT_MB="${WORKSPACE_SOFT_MB:-112}"
# Scratch space for files too big to live in /home/user. NOT snapshotted,
# so anything here vanishes at end of turn (and never counts toward the cap).
BULK_DIR="${BULK_DIR:-/var/tmp}"
# Big binaries go to their own branch so `pull` on main never drags them in.
ASSET_BRANCH="${ASSET_BRANCH:-assets}"
# pack (which commits chunks into the workspace) is only safe for modest files
PACK_SAFE_MB="${PACK_SAFE_MB:-40}"
BRANCH="${BRANCH:-main}"
cd "$REPO_DIR"

say() { printf '\033[1;36m▸ %s\033[0m\n' "$*"; }
ok()  { printf '\033[1;32m✔ %s\033[0m\n' "$*"; }
warn(){ printf '\033[1;33m! %s\033[0m\n' "$*"; }
die() { printf '\033[1;31m✘ %s\033[0m\n' "$*" >&2; exit 1; }

need_repo() {
  [ -d .git ] || die "no git repo in $REPO_DIR — run: $0 init <remote-url>"
  # .git/config is excluded from many workspace snapshots, so the remote can vanish
  # between sessions. Record the (non-secret) URL in a tracked file and self-heal.
  if ! git remote get-url origin >/dev/null 2>&1; then
    if [ -f .gitremote ]; then
      git remote add origin "$(head -1 .gitremote)"
      warn "origin was missing (snapshot dropped .git/config) — restored from .gitremote"
    else
      die "no 'origin' remote configured — run: $0 init <remote-url>"
    fi
  fi
}

# ── size guard: runs before every commit ─────────────────────
file_size_guard() {
  local out; out=$(mktemp)
  git diff --cached --name-only --diff-filter=ACM 2>/dev/null | while IFS= read -r f; do
    [ -f "$f" ] || continue
    local b mb
    b=$(stat -c%s "$f" 2>/dev/null || echo 0)
    mb=$(( b / 1048576 ))
    if [ "$mb" -ge "$MAX_FILE_MB" ]; then
      printf 'BAD|%s|%s\n' "$mb" "$f" >> "$out"
    elif [ "$mb" -ge "$WARN_FILE_MB" ]; then
      printf 'WARN|%s|%s\n' "$mb" "$f" >> "$out"
    fi
  done
  local bad=0 warned=0
  if [ -s "$out" ]; then
    while IFS='|' read -r kind mb f; do
      if [ "$kind" = "BAD" ]; then
        printf '\033[1;31m✘ %5s MB  %s\033[0m\n' "$mb" "$f"; bad=$((bad+1))
      else
        printf '\033[1;33m! %5s MB  %s\033[0m\n' "$mb" "$f"; warned=$((warned+1))
      fi
    done < "$out"
  fi
  rm -f "$out"
  if [ "$bad" -gt 0 ]; then
    git reset -q
    die "$bad file(s) >= ${MAX_FILE_MB} MB — GitHub would reject them.
   Split first:  $0 pack <file>     then:  $0 drop <file>   then push again"
  fi
  [ "$warned" -gt 0 ] && warn "$warned large file(s) committed — fine, but history grows"
  return 0
}

# ── workspace cap guard ──────────────────────────────────────
workspace_guard() {
  local used
  used=$(du -sm --exclude=.git . 2>/dev/null | cut -f1)
  [ -z "$used" ] && return 0
  if [ "$used" -ge "$WORKSPACE_SOFT_MB" ]; then
    warn "workspace at ${used} MB of ${WORKSPACE_MB} MB cap — clean up before the turn ends"
    du -sm --exclude=.git ./* 2>/dev/null | sort -rn | head -5 | awk '{printf "     %s MB  %s\n", $1, $2}'
  fi
}

cmd="${1:-status}"

case "$cmd" in

init)
  URL="${2:-}"; [ -n "$URL" ] || die "usage: $0 init <https-or-ssh-remote-url> [branch]"
  [ -n "${3:-}" ] && BRANCH="$3"

  say "initialising repo in $REPO_DIR (branch $BRANCH)"
  [ -d .git ] || git init -q -b "$BRANCH"
  git symbolic-ref HEAD "refs/heads/$BRANCH" 2>/dev/null || true

  git config user.name  >/dev/null || git config user.name  "Arena Agent"
  git config user.email >/dev/null || git config user.email "agent@arena.local"

  # keep the token out of snapshot-tracked files when using HTTPS
  git config credential.helper store

  # if it's an SSH remote, pin the deploy key for this repo only
  if printf '%s' "$URL" | grep -qE '^(git@|ssh://)'; then
    [ -f "$SSH_KEY" ] || die "SSH remote but no key at $SSH_KEY - run: $0 keygen"
    mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"
    ssh-keyscan -H github.com >> "$HOME/.ssh/known_hosts" 2>/dev/null || true
    sort -u "$HOME/.ssh/known_hosts" -o "$HOME/.ssh/known_hosts" 2>/dev/null || true
    chmod 644 "$HOME/.ssh/known_hosts" 2>/dev/null || true
    git config core.sshCommand "ssh -i $SSH_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
    ok "using deploy key $SSH_KEY for this repo only"
  fi

  git remote get-url origin >/dev/null 2>&1 \
    && git remote set-url origin "$URL" \
    || git remote add origin "$URL"
  printf '%s\n' "$URL" > .gitremote    # survives .git/config being dropped

  cat > .gitignore <<'EOF'
# token / credentials - never commit
.git-credentials
.netrc
*.token
.env
.ssh/
*.pem
*.key
id_ed25519*
id_rsa*
# python
__pycache__/
*.pyc
# os
.DS_Store
Thumbs.db
# reassembled output from large/*.parts — never commit
restored/
# big raw video masters (keep in Drive, export finals instead)
raw_video/
*.mov
*.mkv
EOF

  cat > .gitattributes <<'EOF'
*.png binary
*.jpg binary
*.jpeg binary
*.webp binary
*.psd binary
*.tif binary
*.mp4 binary
# split chunks of large files
large/**/*.part-* binary -diff
large/**/* -text
EOF

  git add -A
  file_size_guard
  git commit -q -m "chore: workspace initialised" || warn "nothing to commit"
  say "fetching remote state"
  if git fetch origin "$BRANCH" 2>/dev/null && git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
    git branch --set-upstream-to="origin/$BRANCH" "$BRANCH" 2>/dev/null || true
    git pull --rebase --autostash origin "$BRANCH" 2>/dev/null || warn "pull skipped"
  else
    warn "remote branch '$BRANCH' not found yet — first push will create it"
  fi
  ok "init done"
  ;;

pull)
  need_repo
  say "pulling origin/$BRANCH"
  # back up uncommitted work first (crash insurance)
  if [ -n "$(git status --porcelain)" ]; then
    STAMP=$(date +%Y%m%d_%H%M%S)
    mkdir -p memory/autosaves
    git diff > "memory/autosaves/uncommitted_${STAMP}.patch" || true
    warn "uncommitted changes stashed to memory/autosaves/uncommitted_${STAMP}.patch"
  fi
  git fetch origin "$BRANCH"
  git pull --rebase --autostash origin "$BRANCH" || die "pull failed — resolve conflicts, then retry"
  ok "up to date at $(git rev-parse --short HEAD) — $(git log -1 --pretty=%s)"
  ;;

push)
  need_repo
  MSG="${2:-autosave $(date '+%Y-%m-%d %H:%M')}"
  git add -A
  file_size_guard
  workspace_guard
  if git diff --cached --quiet; then
    ok "nothing to commit"
  else
    git commit -q -m "$MSG"
    ok "committed: $MSG"
  fi
  # rebase onto remote so the push is a fast-forward — no force needed
  git fetch origin "$BRANCH" >/dev/null 2>&1 || true
  if git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
    git rebase "origin/$BRANCH" >/dev/null 2>&1 || die "rebase conflict — run '$0 status', resolve, retry"
  fi
  say "pushing to origin/$BRANCH (no force)"
  git push origin "HEAD:$BRANCH"          # deliberately NO --force / --force-with-lease
  ok "pushed $(git rev-parse --short HEAD)"
  ;;

keygen)
  mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"
  if [ -f "$SSH_KEY" ]; then
    warn "key already exists at $SSH_KEY - printing public half"
  else
    say "generating ed25519 deploy key"
    ssh-keygen -t ed25519 -C "arena-deploy-$(hostname)-$(date +%Y%m%d)" -f "$SSH_KEY" -N "" -q
    chmod 600 "$SSH_KEY"; chmod 644 "$SSH_KEY.pub"
    ok "created $SSH_KEY"
  fi
  echo
  echo "--- paste this into GitHub: repo > Settings > Deploy keys > Add deploy key ---"
  cat "$SSH_KEY.pub"
  echo "----------------------------------------------------------------------------"
  echo
  echo "Tick [x] Allow write access before saving."
  echo "Then run: $0 init git@github.com:<you>/<repo>.git"
  ;;

pack)
  f="${2:-}"; [ -n "$f" ] || die "usage: $0 pack <file>"
  [ -f "$f" ] || die "no such file: $f"
  base=$(basename "$f")
  fmb=$(( $(stat -c%s "$f") / 1048576 ))
  if [ "$fmb" -ge "$PACK_SAFE_MB" ]; then
    die "$base is ${fmb} MB. 'pack' keeps the chunks inside the workspace, and .git
   would grow by the same amount — that breaks the ${WORKSPACE_MB} MB cap.
   Use:  $0 bulk $f"
  fi
  dir="large/${base}.parts"
  mkdir -p "$dir"
  rm -f "$dir/${base}".part-*
  say "splitting $base into ${CHUNK_MB} MB chunks"
  split -b "${CHUNK_MB}M" -d -a 3 "$f" "$dir/${base}.part-"
  n=$(find "$dir" -name "${base}.part-*" | wc -l)
  bytes=$(stat -c%s "$f")
  sha=$(sha256sum "$f" | cut -d' ' -f1)
  printf '%s  %s\n' "$sha" "$base" > "$dir/${base}.sha256"
  cat > "$dir/manifest.txt" <<MFT
original: $f
bytes: $bytes
sha256: $sha
chunks: $n
chunk_size_mb: $CHUNK_MB
generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
MFT
  cat > "$dir/reassemble.sh" <<'RSEOF'
#!/usr/bin/env bash
# reassemble + verify, run from the repo root:  bash large/<name>.parts/reassemble.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
DIR="$(cd "$(dirname "$0")" && pwd)"
BASE=$(grep -m1 '^original:' "$DIR/manifest.txt" | sed -e 's|^original:[[:space:]]*||' -e 's|.*/||')
OUT="restored/$BASE"
mkdir -p restored
cat "$DIR/${BASE}".part-* > "$OUT"
echo "checking sha256…"
got=$(sha256sum "$OUT" | cut -d' ' -f1)
want=$(cut -d' ' -f1 "$DIR/${BASE}.sha256")
if [ "$got" = "$want" ]; then echo "✔ restored $OUT (sha256 ok)"; else echo "✘ hash mismatch"; exit 1; fi
RSEOF
  chmod +x "$dir/reassemble.sh"
  # keep the un-split original out of git without deleting it (local-only ignore)
  mkdir -p .git/info
  grep -qxF "$f" .git/info/exclude 2>/dev/null || echo "$f" >> .git/info/exclude
  ok "packed: $base -> $dir ($n chunks, sha256 ${sha:0:12}…)"
  echo "   next:  $0 push \"add large/$base\"   then   $0 drop $f"
  ;;

unpack)
  dir="${2:-}"; [ -n "$dir" ] || die "usage: $0 unpack large/<name>.parts"
  if [ -d "$dir" ]; then
    [ -f "$dir/reassemble.sh" ] || die "$dir has no reassemble.sh"
    bash "$dir/reassemble.sh"
  elif [ -d "large/${dir}.parts" ]; then
    bash "large/${dir}.parts/reassemble.sh"
  else
    die "no such parts dir: $dir"
  fi
  ;;

drop)
  f="${2:-}"; [ -n "$f" ] || die "usage: $0 drop <file>   (only works once packed)"
  [ -f "$f" ] || die "no such file: $f"
  base=$(basename "$f")
  dir="large/${base}.parts"
  [ -d "$dir" ] || die "not packed — run '$0 pack $f' first"
  want=$(cut -d' ' -f1 "$dir/${base}.sha256" 2>/dev/null || true)
  have=$(sha256sum "$f" | cut -d' ' -f1)
  [ "$want" = "$have" ] || die "sha256 mismatch vs manifest — refusing to delete $f"
  git add "$dir" >/dev/null 2>&1 || true
  sz=$(du -sm "$f" | cut -f1)
  rm -f "$f"
  ok "dropped $f (freed ~${sz} MB); restore with: $0 unpack $dir"
  workspace_guard
  ;;

bulk)
  f="${2:-}"; shift 2 2>/dev/null || true
  RM=0; KEEP=0
  for a in "$@"; do
    case "$a" in
      --rm) RM=1 ;;
      --keep) KEEP=1 ;;
      *) die "unknown flag: $a (use --rm / --keep)" ;;
    esac
  done
  [ -n "$f" ] || die "usage: $0 bulk <file> [--rm] [--keep]"
  [ -f "$f" ] || die "no such file: $f"
  need_repo

  remote=$(git remote get-url origin)
  base=$(basename "$f")
  bytes=$(stat -c%s "$f"); mb=$(( bytes / 1048576 ))
  say "bulk: $base (${mb} MB) -> branch '$ASSET_BRANCH' via scratch space in $BULK_DIR"
  say "main and the workspace are NOT touched by the data"

  WORK=$(mktemp -d "$BULK_DIR/arena-bulk.XXXXXX")
  trap '[ "${KEEP:-0}" = "1" ] && warn "keeping $WORK" || rm -rf "$WORK"' EXIT
  R="$WORK/repo"

  # prefer the assets branch (so repeat bulks fast-forward); else start from main
  if git clone -q --depth 1 -b "$ASSET_BRANCH" "$remote" "$R" 2>/dev/null; then
    say "cloned existing '$ASSET_BRANCH' branch"
  else
    rm -rf "$R"
    if ! git clone -q --depth 1 -b "$BRANCH" "$remote" "$R" 2>/dev/null; then
      mkdir -p "$R"; git -C "$R" init -q -b "$ASSET_BRANCH"
      git -C "$R" remote add origin "$remote"
    fi
    git -C "$R" checkout -q -B "$ASSET_BRANCH"
    say "starting '$ASSET_BRANCH' from '$BRANCH'"
  fi
  git -C "$R" config user.name  "$(git config user.name  || echo 'Arena Agent')"
  git -C "$R" config user.email "$(git config user.email || echo 'agent@arena.local')"

  parts="$R/large/${base}.parts"
  mkdir -p "$parts"
  say "splitting into ${CHUNK_MB} MB chunks"
  split -b "${CHUNK_MB}M" -d -a 3 "$f" "$parts/${base}.part-"
  n=$(find "$parts" -name "${base}.part-*" | wc -l)
  sha=$(sha256sum "$f" | cut -d' ' -f1)
  printf '%s  %s\n' "$sha" "$base" > "$parts/${base}.sha256"
  cat > "$parts/manifest.txt" <<MFT
original: $base
bytes: $bytes
sha256: $sha
chunks: $n
chunk_size_mb: $CHUNK_MB
branch: $ASSET_BRANCH
generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
restored_to: restored/$base
MFT
  cat > "$parts/reassemble.sh" <<'RSEOF'
#!/usr/bin/env bash
# rejoin the chunks and verify. Run from anywhere:
#   bash large/<name>.parts/reassemble.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
BASE=$(grep -m1 '^original:' "$DIR/manifest.txt" | sed -e 's|^original:[[:space:]]*||' -e 's|.*/||')
OUT="$DIR/../../restored/$BASE"
mkdir -p "$(dirname "$OUT")"
cat "$DIR/${BASE}".part-* > "$OUT"
got=$(sha256sum "$OUT" | cut -d' ' -f1)
want=$(cut -d' ' -f1 "$DIR/${BASE}.sha256")
if [ "$got" = "$want" ]; then echo "OK restored $OUT (sha256 ok)"; else echo "FAIL hash mismatch"; exit 1; fi
RSEOF
  chmod +x "$parts/reassemble.sh"

  say "committing ${n} chunk(s) (${mb} MB) on '$ASSET_BRANCH'"
  git -C "$R" add -A
  git -C "$R" commit -q -m "bulk: ${base} as ${n} chunks (${mb} MB, sha256 ${sha:0:12})"
  say "pushing to $remote ($ASSET_BRANCH)"
  git -C "$R" push -q origin "HEAD:refs/heads/$ASSET_BRANCH" || die "push failed"

  landed=$(git -C "$R" ls-tree -r --name-only HEAD | grep -c "large/${base}.parts/${base}.part-" || true)
  remote_sha=$(git -C "$R" ls-remote origin "refs/heads/$ASSET_BRANCH" | cut -f1)
  local_sha=$(git -C "$R" rev-parse HEAD)
  if [ "$landed" -eq "$n" ] && [ "$remote_sha" = "$local_sha" ]; then
    ok "verified: ${landed}/${n} chunks live on origin/$ASSET_BRANCH (${remote_sha:0:7})"
  else
    warn "verification mismatch — chunks:$landed/$n remote:${remote_sha:0:7} local:${local_sha:0:7}"
  fi

  # only the tiny metadata goes into the workspace and onto main
  mkdir -p "large/${base}.parts_meta"
  cp "$parts/manifest.txt" "$parts/${base}.sha256" "$parts/reassemble.sh" "large/${base}.parts_meta/"
  cat >> "large/${base}.parts_meta/README.txt" <<MFT
chunks live on branch '$ASSET_BRANCH' of $remote
nothing large is stored in the workspace or on main, so 'pull' stays cheap.

restore in a fresh clone:
  git clone -b $ASSET_BRANCH --single-branch $remote
  cd <repo> && bash large/${base}.parts/reassemble.sh

restore into an existing clone:
  git fetch origin $ASSET_BRANCH
  git checkout origin/$ASSET_BRANCH -- large/${base}.parts
  bash large/${base}.parts/reassemble.sh
MFT
  git add "large/${base}.parts_meta"
  git commit -q -m "meta: record ${base} on branch $ASSET_BRANCH (${mb} MB, ${n} chunks)" 2>/dev/null \
    && say "metadata committed to main" || warn "metadata commit skipped"

  if [ "$RM" = "1" ]; then
    rm -f "$f"
    ok "deleted $f (${mb} MB freed)"
  else
    warn "source still at $f — remove it when happy: rm '$f'"
  fi
  echo
  echo "sha256:  $sha"
  echo "restore: git clone -b $ASSET_BRANCH --single-branch $remote && cd \$(basename ${remote%.git}) && bash large/${base}.parts/reassemble.sh"
  echo "then:    $0 push \"meta: $base\"   (main is a few KB lighter, not a few hundred)"
  ;;

sizecheck)
  used=$(du -sm --exclude=.git . 2>/dev/null | cut -f1)
  gitsz=$(du -sm .git 2>/dev/null | cut -f1)
  tracked=$(git ls-files 2>/dev/null | wc -l)
  echo "workspace (excl .git): ${used} MB / ${WORKSPACE_MB} MB sandbox cap"
  echo ".git:                  ${gitsz} MB"
  echo "tracked files:         ${tracked}"
  echo "largest 8 files:"
  find . -path ./.git -prune -o -type f -printf '%s %p\n' 2>/dev/null \
    | sort -rn | head -8 | awk '{printf "  %6.1f MB  %s\n", $1/1048576, $2}'
  echo "split chunks present:"
  find large -name '*.part-*' 2>/dev/null | wc -l | awk '{print "  "$1" chunk(s)"}'
  if [ "$used" -ge "$WORKSPACE_SOFT_MB" ]; then
    warn "over the ${WORKSPACE_SOFT_MB} MB soft line — free space before ending the turn"
  else
    ok "within budget ($(( WORKSPACE_MB - used )) MB headroom)"
  fi
  ;;

status)
  need_repo
  echo "repo:    $REPO_DIR"
  echo "remote:  $(git remote get-url origin)"
  echo "branch:  $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo none)"
  echo "head:    $(git rev-parse --short HEAD 2>/dev/null || echo none)"
  echo "changes:"; git status --porcelain | head -30
  echo "last 5:"; git log --oneline -5 2>/dev/null || true
  ;;

doctor)
  need_repo
  say "checking auth to $(git remote get-url origin)"
  git ls-remote --heads origin >/dev/null 2>&1 \
    && ok "auth works (read)" \
    || die "cannot read remote — token missing/expired (re-provision ~/.git-credentials), or URL wrong"
  say "checking push permission without changing anything"
  git push --dry-run origin "HEAD:$BRANCH" >/dev/null 2>&1 \
    && ok "push permitted" \
    || warn "push dry-run failed — check Contents: Read and write"
  case "$(git remote get-url origin)" in
    git@*|ssh://*)
      say "SSH mode - testing deploy key"
      if ssh -i "$SSH_KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 | grep -qi "successfully authenticated"; then
        ok "deploy key accepted by GitHub"
      else
        warn "ssh -T git@github.com did not confirm auth (git may still work)"
      fi
      ;;
  esac
  say "confirming script will never force push"
  if sed 's/#.*//' "$0" | grep -Eq 'git[[:space:]]+push[^|;]*--force'; then
    warn "found a destructive push flag in this script — remove it!"
  else
    ok "no force-pushing git commands in this script"
  fi
  ;;

*)
  die "unknown command '$cmd' (init|keygen|pack|unpack|drop|bulk|sizecheck|pull|push|status|doctor)"
  ;;
esac
