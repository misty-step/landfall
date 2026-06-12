# Build a fleet adoption planner

Priority: P0 · Status: pending · Estimate: XL

## Goal
Let Landfall scan personal and Mistystep GitHub repositories, classify adoption readiness, and open safe per-repo installation pull requests with minimal manual setup.

## Oracle
- [ ] `dist/landfall fleet scan --owner phrazzld --owner misty-step --output .landfall/fleet.json` lists repositories, activity, release tooling, default branch, tag format, package topology, existing workflows, and required secret status without mutating remote state.
- [ ] `dist/landfall fleet plan --input .landfall/fleet.json --output-dir .landfall/fleet-plan` emits a ranked adoption plan with skip reasons, risk flags, and recommended Landfall mode for each active repo.
- [ ] `dist/landfall fleet open-prs --dry-run` renders per-repo workflow and manifest diffs without pushing branches.
- [ ] A replay or fixture test covers at least semantic-release, release-please, changesets, manual-tag, no-release-tool, archived, private, and branch-protected repository cases.
- [ ] The command never prints secret values and clearly reports missing token scopes or unavailable secret metadata.

## Children
1. Add read-only GitHub inventory for repo metadata, recent activity, default branch, release files, tags, workflows, and package signals.
2. Extend setup diagnosis into a fleet classification model: full mode, synthesis-only mode, backfill first, manifest only, blocked, skipped.
3. Add secret and permission readiness checks that work for org repos and degrade honestly for personal repos where GitHub APIs hide details.
4. Generate per-repo adoption branches or PR plans with `.landfall.yml`, workflow files, artifact paths, and migration notes.
5. Add batching controls: active-only, dry-run, max PRs, owner filters, allow/deny lists, and existing-release-tool collision handling.
6. Produce a fleet report that becomes the operator dashboard for phased rollout across personal and Mistystep repositories.

## Notes
- Evidence: `gh repo list phrazzld --limit 200` returned 153 repositories and `gh repo list misty-step --limit 200` returned 73, making manual adoption too expensive and error-prone.
- Evidence: current `landfall setup` can analyze one checkout and emit candidate workflows, but there is no cross-repo inventory, PR generation, or secret readiness loop.
- Why: the adoption critic ranked org-scale rollout highest because it creates real-world usage data and makes every later synthesis/cost feature more grounded.
