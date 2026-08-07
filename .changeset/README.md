# Changesets

This project uses [Changesets](https://github.com/changesets/changesets) for version bumps and `CHANGELOG.md`. There is no npm publish — the version in `package.json` is the source of truth for Docker image semver tags.

## Policy

- Work on a **feature branch** that includes the Bead issue ID(s) — never commit product work on `main` (see `AGENTS.md` / `CLAUDE.md`)
- **Every commit with a meaningful change must include a new changeset** under this directory
- Meaningful = features, fixes, behavior/API changes, user-facing docs, Docker/runtime. When unsure, use `patch`

## After a meaningful change

### Humans (interactive)

```bash
npm run changeset
# pick patch | minor | major, write a short summary
git add .changeset
git commit -m "feat: your change"
```

### Agents (non-interactive — required)

Do **not** run interactive `npm run changeset`. Write a file directly:

```markdown
---
"job-hunter": patch
---

Short summary of the change for CHANGELOG.md
```

Save as `.changeset/<unique-kebab-name>.md`, stage it with the code change, and commit on the feature branch.

## Release flow

When the change lands on `main`, the Changesets GitHub Action opens (or updates) a **Version Packages** PR. Merging that PR bumps the version, updates the changelog, and triggers a Docker release with the new semver tag.
