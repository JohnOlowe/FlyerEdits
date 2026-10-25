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
#   Deploy-key (SSH) mode:
#   ./scripts/git_sync.sh keygen           # make an ed25519 keypair, print pubkey
#   ./scripts/git_sync.sh init git@github.com:<you>/<repo>.git
# ─────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/user}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/arena_deploy_ed25519}"
BRANCH="${BRANCH:-main}"
cd "$REPO_DIR"

say() { printf '\033[1;36m▸ %s\033[0m\n' "$*"; }
ok()  { printf '\033[1;32m✔ %s\033[0m\n' "$*"; }
warn(){ printf '\033[1;33m! %s\033[0m\n' "$*"; }
die() { printf '\033[1;31m✘ %s\033[0m\n' "$*" >&2; exit 1; }

need_repo() {
  [ -d .git ] || die "no git repo in $REPO_DIR — run: $0 init <remote-url>"
  git remote get-url origin >/dev/null 2>&1 || die "no 'origin' remote configured"
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
*.mp4 binary diff=lfs
EOF

  git add -A
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
    || die "cannot read remote — token wrong/expired, or URL wrong"
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
  die "unknown command '$cmd' (init|keygen|pull|push|status|doctor)"
  ;;
esac
