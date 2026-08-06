# Changesets

This project uses [Changesets](https://github.com/changesets/changesets) for version bumps and `CHANGELOG.md`. There is no npm publish — the version in `package.json` is the source of truth for Docker image semver tags.

## After a user-facing change

```bash
npm run changeset
# pick patch | minor | major, write a short summary
git add .changeset
git commit -m "feat: your change"
```

When the change lands on `main`, the Changesets GitHub Action opens (or updates) a **Version Packages** PR. Merging that PR bumps the version, updates the changelog, and triggers a Docker release with the new semver tag.
