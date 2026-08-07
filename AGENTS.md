# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd prime` for full workflow context.

> **Architecture in one line:** Issues live in a local Dolt database
> (`.beads/dolt/`); cross-machine sync uses `bd dolt push/pull` (a
> git-compatible protocol), stored under `refs/dolt/data` on your git
> remote — separate from `refs/heads/*` where your code lives.
> `.beads/issues.jsonl` is a passive export, not the wire protocol.
>
> See [SYNC_CONCEPTS.md](https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md)
> for the one-screen overview and anti-patterns (don't treat JSONL as the
> source of truth; don't `bd import` during normal operation; don't
> reach for third-party Dolt hosting before trying the default).

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work atomically
bd close <id>         # Complete work
bd dolt push          # Push beads data to remote
```

## Non-Interactive Shell Commands

**ALWAYS use non-interactive flags** with file operations to avoid hanging on confirmation prompts.

Shell commands like `cp`, `mv`, and `rm` may be aliased to include `-i` (interactive) mode on some systems, causing the agent to hang indefinitely waiting for y/n input.

**Use these forms instead:**
```bash
# Force overwrite without prompting
cp -f source dest           # NOT: cp source dest
mv -f source dest           # NOT: mv source dest
rm -f file                  # NOT: rm file

# For recursive operations
rm -rf directory            # NOT: rm -r directory
cp -rf source dest          # NOT: cp -r source dest
```

**Other commands that may prompt:**
- `scp` - use `-o BatchMode=yes` for non-interactive
- `ssh` - use `-o BatchMode=yes` to fail instead of prompting
- `apt-get` - use `-y` flag
- `brew` - use `HOMEBREW_NO_AUTO_UPDATE=1` env var

## Git branching (mandatory)

**NEVER commit or push work directly on `main`.** Always work on a feature branch.

### Before writing code

1. Check current branch: `git branch --show-current`
2. If you are on `main` (or another branch unrelated to this work), create and switch to a new branch
3. If you are **already** on a branch that clearly belongs to this work (includes the bead ID(s)), keep using it

### Branch naming

Include the **Bead issue ID(s)** you are working on:

```text
<bead-id>[-<bead-id2>...]-short-description
```

Examples:

```bash
# Single issue
git checkout -b job-hunter-21r-strict-location-filters

# Multiple related issues in one branch
git checkout -b job-hunter-1jl-job-hunter-uo5-boards-and-location
```

Rules:

- Always include at least one full bead ID (e.g. `job-hunter-21r`)
- Use lowercase kebab-case for the short description
- Do not use generic names like `fix`, `wip`, or `agent-work` without a bead ID
- Prefer branching from an up-to-date `main`: `git fetch origin && git checkout -b <branch> origin/main`

### Session workflow (branch + beads)

```bash
bd ready                              # or bd show <id>
bd update <id> --claim
git checkout -b <bead-id>-short-desc  # if not already on a relevant branch
# ... implement ...
# changeset (see below) + commit + push branch
```

Push the **feature branch**, not `main`. Open/update a PR when the work is ready to land.

## Changesets (mandatory for meaningful commits)

This project uses [Changesets](https://github.com/changesets/changesets). The version in `package.json` drives Docker image tags and `CHANGELOG.md`.

**Any commit that includes a meaningful change MUST include a new changeset file** under `.changeset/`.

### What counts as meaningful

**Require a changeset for:**

- Features, bug fixes, refactors that change behavior
- API / config / schema / scoring / scraping changes
- User-facing docs, Docker/runtime behavior, release-related changes

**Skip a changeset only for:**

- Pure chore with no product impact (e.g. formatting-only, beads metadata-only)
- Reverts that only remove an unreleased changeset
- WIP commits that you will squash before merge **and** the final squash/merge commit still includes a changeset

If unsure, add a `patch` changeset.

### How agents create a changeset (non-interactive)

Do **not** run interactive `npm run changeset` (it hangs agents). Write a markdown file under `.changeset/` instead:

```bash
# filename: short-kebab-description.md (unique; human-id style is fine)
```

```markdown
---
"job-hunter": patch
---

Short summary of the change for CHANGELOG.md
```

Bump levels:

| Level   | When |
|---------|------|
| `patch` | Bug fixes, small improvements, docs that ship with the product |
| `minor` | New features, backward-compatible capability |
| `major` | Breaking changes |

Include the new `.changeset/*.md` file in the **same commit** as the meaningful code change (or the commit that finalizes that change on the branch).

See `.changeset/README.md` for release-flow details (Version Packages PR on `main`).

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:7510c1e2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
