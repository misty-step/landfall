# Add real --help text to every CLI subcommand and flag

Priority: P2 · Status: ready · Estimate: M

## Goal
`landmark --help` and every subcommand's `--help` currently render blank
descriptions for all 28 subcommands and nearly every flag. Add clap doc
comments (`///`) so the CLI is self-describing for cold agents and humans,
matching the agent-native-contract bar the rest of the repo already holds
itself to.

## Oracle
- [ ] `cargo run --locked -- --help` shows a non-empty one-line description for
      every subcommand listed under `Commands:` (currently: `describe`, `init`,
      `doctor`, `manifest-defaults`, `healthcheck`, `preflight-tags`,
      `fetch-release-body`, `extract-prs`, `synthesize`, `release-policy`,
      `update-release`, `write-artifacts`, `update-feed`, `notify-webhook`,
      `notify-slack`, `run`, `floating-tag`, `close-resolved-failures`,
      `report-synthesis-failure`, `update-version-metadata`,
      `check-version-sync`, `check-action-contract`, `replay-action`,
      `backfill`, `setup`, `fleet`, `prepare-self-release`,
      `publish-self-release`).
- [ ] `cargo run --locked -- run --help`, `synthesize --help`, `backfill
      --help`, `setup --help`, `fleet --help`, and `prepare-self-release
      --help` (the highest-traffic subcommands per README/agent-integration
      guide) show a non-empty description for every flag, not just its type
      and default.
- [ ] Descriptions are accurate against current behavior (source from README/
      `docs/agent-integration.md`/existing doc comments elsewhere in the repo
      where they already explain a flag; do not invent new semantics).
- [ ] `bin/gate` passes (including `cargo clippy -D warnings`, which will
      catch any malformed doc comments).

## Notes
Verified live: `cargo run --locked -q -- --help` prints every subcommand with
a blank description; `cargo run --locked -q -- run --help` prints every flag
(`--provider`, `--repo-root`, `--dry-run`, `--output-dir`, etc.) with no help
text, only `[default: ...]`. `crates/landmark/src/cli.rs` (673 lines) has
essentially zero `///` doc comments on its `#[derive(Parser)]`/`#[derive(Args)]`
structs today (only the top-level `#[command(about = "...")]` on line 5 has
text). clap renders `///` comments as `--help` output automatically — no
new dependency or mechanism needed, purely additive doc comments.

This directly serves AGENTS.md's own standing rule: "Keep README, action.yml,
examples, and this file aligned. Stale agent-facing prose is a release risk
because agents use it as an operating contract" — the CLI's own `--help` is
the most agent-native surface of all and is currently silent. Large surface
area (28 subcommands); land it incrementally if needed (top-level `about`
text first, then flag-level help for the highest-traffic subcommands named
above), but the oracle above is the floor for calling this done.

**Why:** live-verified via direct `--help` invocation during this groom pass,
not inferred from the teardown report (which did not flag this specific gap).
