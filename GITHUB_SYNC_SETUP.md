# GitHub sync setup — scoped token **or** deploy key, force-push blocked on this repo only

Two questions answered here:

1. **"I only want force-push disabled on this one repo — I use it normally elsewhere."**
   → Section A. Short answer: that's exactly what a **repository ruleset** does. Nothing global changes.
2. **"What does the deploy key require, and how does it compare?"**
   → Section C, with a side-by-side table.

---

# A. Blocking force-push on **one repo only**

There are two levels of rulesets. You want the first one:

| Level | Where | Scope |
|---|---|---|
| **Repository ruleset** ✅ | **Repo → Settings → Rules → Rulesets** | **this repo only** — everything else you own is untouched |
| Organization ruleset ❌ | Org → Settings → Rules → Rulesets | every repo in the org — this is the one that would change your habits |

So: make sure you're inside **the repository's** Settings page, not your account or org settings.

### Steps
**Repo → Settings → Rules → Rulesets → New branch ruleset**

| Field | Value |
|---|---|
| Ruleset name | `protect-main` |
| Enforcement status | **Active** |
| Target branches | **Add target → Include default branch** (just `main`) |
| ✅ | **Block force pushes** |
| ✅ | **Restrict deletions** |
| Bypass list | **leave empty** |

### What this does and doesn't affect

- **Your other repos:** a `git push --force` there works exactly as before. This ruleset has no reach outside this repo.
- **Your own habits:** the token/key I use is just a credential. It doesn't change how *you* push anywhere.
- **Branches inside this repo:** the block applies only to the branches you target. Target `main` only, and you can still force-push a throwaway feature branch in this repo if you want. Target **Include all branches** if you want the whole repo locked.
- **`--force-with-lease`:** also blocked. GitHub treats it as a force push.

### The escape hatch (and why it's safe)
If you ever *need* to rewrite `main` in this repo: set the ruleset's enforcement to **Disabled** in the browser, do your thing, set it back.

I **cannot** do that. My token has only `Contents: Read and write` — no `Administration` permission — so it can't read, edit, or disable the ruleset. A deploy key is even further away from it (it isn't an admin identity at all). Deliberate, and worth keeping.

⚠️ **Plan caveat, unchanged:** rulesets / branch protection on a **private** repo require **GitHub Pro** (~$4/mo) or Team. On the **Free** plan they only enforce on **public** repos. Private + Free = GitHub will not enforce it, and the only guard left is my script, which contains no `--force` anywhere.

---

# B. Option 1 — Fine-grained PAT (minimum access, one repo)

1. **https://github.com/settings/personal-access-tokens/new**
2. Name `arena-graphics-sync`, expiration **7 days**
3. **Repository access:** ⦿ *Only select repositories* → the one repo
4. **Permissions:** **Contents → Read and write**. Nothing else. (Metadata auto-sets read-only and can't be removed.)
5. Generate, copy `github_pat_…`

Grants clone/pull/push on that repo and nothing else — no other repos, no profile, no settings, no workflows, no org.

---

# C. Option 2 — Deploy key

### Requirements
1. **Admin on the repo** (you, in the browser) to add the key.
2. **An SSH keypair.** I generate it: `./scripts/git_sync.sh keygen` → prints the `ssh-ed25519 …` public half. Private half stays at `~/.ssh/arena_deploy_ed25519` with `600` perms.
3. **Repo → Settings → Deploy keys → Add deploy key** → paste the **public** key → tick **☑ Allow write access** → save. (Without the write tick it's read-only.)
4. **SSH remote URL**, not HTTPS: `git@github.com:<you>/<repo>.git`
5. `github.com` must be in `known_hosts` — the script does `ssh-keyscan` for you.
6. **One repo per key.** GitHub rejects the same key on a second repo; a new repo needs a new key.
7. Available on any plan, including Free, private repos.

### Setup
```bash
./scripts/git_sync.sh keygen                                    # prints public key
#   → paste into GitHub, tick "Allow write access"
./scripts/git_sync.sh init git@github.com:<you>/<repo>.git      # pins the key repo-locally
./scripts/git_sync.sh doctor                                    # verifies the key is accepted
```
The script sets a repo-local `core.sshCommand` (`-i <key> -o IdentitiesOnly=yes -o BatchMode=yes`), so that key is offered for **this repo only** and never interferes with your own SSH identities.

---

# D. Deploy key vs fine-grained PAT

| | **Deploy key** | **Fine-grained PAT** |
|---|---|---|
| Scope | one repo, by construction | one repo, by configuration |
| Granularity | write = whole repo's contents | can be narrowed per permission |
| **Can it touch repo settings / rulesets?** | **No — never an admin** | No, *unless* you grant Administration |
| **Can it disable the force-push block?** | **Structurally impossible** | Possible only with Administration (not granted) |
| **Expiry** | **none** (manual revoke) | required, max 366 days |
| Renewal churn | none | renew every N days or sync breaks |
| Blast radius if leaked | push files to that one repo | push files to that one repo (same, given our scoping) |
| Works if you change password / reset 2FA | ✅ unaffected | ✅ unaffected |
| Org PAT-approval / SSO policies | ✅ unaffected | may be blocked |
| GitHub **API** access (PRs, issues, releases, Actions) | ❌ none | ✅ yes |
| Works with `gh` CLI | ❌ | ✅ |
| Reuse across repos | ❌ one key per repo | ✅ one token, many repos |
| Commit attribution | as the deploy key — set `user.name`/`user.email` so history looks right | as the PAT's owner |
| Revocation | delete in repo Settings → Deploy keys (one click) | delete token in account settings |
| Setup friction | needs SSH URL + known_hosts | just an HTTPS URL |
| Key storage | private key in `~/.ssh` — **persists in workspace snapshots** so a crash can't lock us out | token in `~/.git-credentials` — excluded from snapshots |

### What I'd pick for us
**Deploy key.** Our job is pull → generate layers → push, in one repo, no API calls. The deploy key is strictly less privilege (it *cannot* be an admin, so it can never undo the force-push rule), it has no expiry to babysit mid-project, and revoking it is one click in the repo.

Trade-offs you're accepting:
- **No expiry is a real risk** if the key ever leaks unnoticed → delete it when the project ends.
- **No API access** → if we later want PRs, releases, or to trigger Actions from here, we add a PAT too.

Choose the **PAT** instead if you want the option of API features later, or if you'd rather revoke from your account than from the repo.

### Handling the credential
- PAT → `~/.git-credentials` (git-ignored, excluded from snapshots)
- Deploy key → `~/.ssh/arena_deploy_ed25519` (git-ignored via `.ssh/`, but **does** persist in snapshots — that's what keeps the sync alive after a crash)
- Either way: never committed, never in a filename, never in a tracked file

---

# E. The sync routine

```bash
./scripts/git_sync.sh pull              # START of every turn
./scripts/git_sync.sh push "bg v3 done" # after each meaningful step
./scripts/git_sync.sh push "turn N: …"  # END of every turn
./scripts/git_sync.sh status
./scripts/git_sync.sh doctor            # verify auth + push rights
```

- `pull` first saves uncommitted work to `memory/autosaves/*.patch`, then `fetch` + `pull --rebase --autostash`
- `push` commits, rebases onto the remote (so it's a plain fast-forward), then `git push` with **no `--force`**
- `.gitignore` covers `.git-credentials`, `.netrc`, `*.token`, `.env`, `.ssh/`, `*.pem`, `*.key`, `id_ed25519*`, `raw_video/`, `*.mov`, `*.mkv`

Repo hygiene: GitHub caps files at **100 MB**; keep raw video out (Drive or Git LFS), commit the layer PNGs — each push is a restore point that can't be erased.
