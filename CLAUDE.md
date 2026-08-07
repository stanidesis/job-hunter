# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

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


## Build & Test

_Add your build and test commands here_

```bash
# Example:
# npm install
# npm test
```

## Architecture Overview

_Add a brief overview of your project architecture_

## Conventions & Patterns

### Git: never work on `main`

- **Do not** commit or push product work on `main`
- Before implementing, check `git branch --show-current`
- If not already on a branch for this work, create one from up-to-date `main`
- Branch name **must include the Bead issue ID(s)** being worked:

```bash
git fetch origin
git checkout -b <bead-id>-short-description origin/main
# e.g. job-hunter-21r-strict-location-filters
# multi-issue: job-hunter-1jl-job-hunter-uo5-boards-and-location
```

- Claim the issue: `bd update <id> --claim`
- Push the feature branch (not `main`); open a PR to merge

### Changesets: required on meaningful commits

Any commit with a **meaningful** change (features, fixes, behavior, API, user-facing docs, Docker/runtime) **must** add a changeset under `.changeset/`.

Agents must create the file **non-interactively** (do not use interactive `npm run changeset`):

```markdown
---
"job-hunter": patch
---

Short summary for the changelog
```

Use `patch` / `minor` / `major` as appropriate. Stage the `.changeset/*.md` with the same commit as the change. See `AGENTS.md` and `.changeset/README.md` for full rules.
