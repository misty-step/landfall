# Add a Landfall product manifest

Priority: P0 · Status: pending · Estimate: L

## Goal
Make each repository's release context, audience, artifact policy, and cost posture durable in `.landfall.yml` instead of scattering it through workflow inputs.

## Oracle
- [ ] `dist/landfall init --repo-root . --output .landfall.yml --dry-run` emits a valid manifest seeded from observable repository metadata.
- [ ] `dist/landfall setup --repo-root . --output-dir .landfall/setup` reads `.landfall.yml` and reflects manifest values in generated workflows.
- [ ] `dist/landfall synthesize ...` uses manifest `product`, `audience`, `voice`, artifact, and model policy defaults when equivalent action inputs are absent.
- [ ] `cargo run --locked -- check-action-contract` fails when README, action inputs, or manifest schema docs drift.
- [ ] `bin/gate` exits 0 and replay evidence covers manifest defaults plus action-input override precedence.

## Children
1. Define `.landfall.yml` schema for product name, audience, description, voice guide, changelog source, artifact outputs, release profile, model policy, and budget hints.
2. Add `landfall init` to infer a first manifest from README, package metadata, repository name, release tool, and existing Landfall inputs.
3. Teach setup generation and synthesis to load the manifest, with explicit action inputs retaining precedence.
4. Add `landfall doctor` checks for missing, stale, contradictory, or overbroad manifest fields.
5. Document manifest-first adoption and update the contract checker to validate examples and schema snippets.

## Notes
- Evidence: `action.yml` already exposes `audience`, `product-description`, `voice-guide`, `prompt-template-path`, `changelog-source`, and artifact outputs, but consumers must repeat those choices in workflow YAML.
- Evidence: `landfall setup` currently diagnoses release tooling and emits workflows, but it does not write repo-native product context artifacts.
- Why: both product/adoption and technical/economics critics identified the manifest as the keystone that makes fleet rollout, cheap synthesis, previews, and backfill composable.
