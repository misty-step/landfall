# Landfall

Landfall is a focused release pipeline GitHub Action for repositories that use conventional commits.
It runs `semantic-release` to publish a version and changelog, then optionally synthesizes user-facing notes with Moonshot/Kimi and prepends them to the GitHub Release body.

## What It Does

1. Sets up Node.js and Python 3.12
2. Installs `semantic-release` and release plugins
3. Runs `semantic-release` (version bump, changelog update, release creation)
4. Optionally synthesizes user-facing notes from technical changelog content
5. Updates the GitHub Release body to prepend a `## What's New` section

## Quick Start

Create `.github/workflows/release.yml` in your repository:

```yaml
name: Release

on:
  push:
    branches:
      - main
      - master

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Run Landfall
        uses: misty-step/landfall@v1
        with:
          github-token: ${{ secrets.GH_RELEASE_TOKEN }}
          moonshot-api-key: ${{ secrets.MOONSHOT_API_KEY }}
```

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `github-token` | Yes | - | Personal access token with repo write access. Used by `semantic-release` and GitHub API update calls. |
| `moonshot-api-key` | Yes | - | API key for Moonshot/Kimi synthesis. |
| `moonshot-model` | No | `kimi-k2.5` | Moonshot model ID for note synthesis. |
| `node-version` | No | `22` | Node.js version used to run `semantic-release`. |
| `synthesis` | No | `true` | If `true`, generate and prepend user-facing notes. |

## Outputs

| Output | Description |
| --- | --- |
| `released` | `true` if a new release/tag was created, otherwise `false`. |
| `release-tag` | Tag created by `semantic-release` (empty if no release). |

## Default semantic-release Config

Landfall ships `configs/.releaserc.json` with:

- `@semantic-release/commit-analyzer`
- `@semantic-release/release-notes-generator`
- `@semantic-release/changelog`
- `@semantic-release/npm` (`npmPublish: false`)
- `@semantic-release/git`
- `@semantic-release/github`

## Example: Technical vs User-Facing

Technical release notes (generated):

```markdown
### Features
- add workspace import command (#214)

### Bug Fixes
- handle retries when webhook signature is stale (#229)

### Chores
- bump ci cache key
```

Synthesized `## What's New` section (prepended):

```markdown
## What's New

## New Features
- You can now import workspace configuration in one command, reducing setup time.

## Bug Fixes
- Webhook deliveries now retry more reliably when signatures expire.
```

Landfall intentionally omits internal-only changes (CI/tooling) from user-facing summaries.
