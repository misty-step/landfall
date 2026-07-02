# Add real --help text to every CLI subcommand and flag

Priority: P2 · Status: done · Estimate: M

## Goal
`landmark --help` and every subcommand's `--help` currently render blank
descriptions for all 28 subcommands and nearly every flag. Add clap doc
comments (`///`) so the CLI is self-describing for cold agents and humans,
matching the agent-native-contract bar the rest of the repo already holds
itself to.

## Oracle
- [x] `cargo run --locked -- --help` shows a non-empty one-line description for
      every subcommand listed under `Commands:` (currently: `describe`, `init`,
      `doctor`, `manifest-defaults`, `healthcheck`, `preflight-tags`,
      `fetch-release-body`, `extract-prs`, `synthesize`, `release-policy`,
      `update-release`, `write-artifacts`, `update-feed`, `notify-webhook`,
      `notify-slack`, `run`, `floating-tag`, `close-resolved-failures`,
      `report-synthesis-failure`, `update-version-metadata`,
      `check-version-sync`, `check-action-contract`, `replay-action`,
      `backfill`, `setup`, `fleet`, `prepare-self-release`,
      `publish-self-release`).
- [x] `cargo run --locked -- run --help`, `synthesize --help`, `backfill
      --help`, `setup --help`, `fleet --help`, and `prepare-self-release
      --help` (the highest-traffic subcommands per README/agent-integration
      guide) show a non-empty description for every flag, not just its type
      and default.
- [x] Descriptions are accurate against current behavior (source from README/
      `docs/agent-integration.md`/existing doc comments elsewhere in the repo
      where they already explain a flag; do not invent new semantics).
- [x] `bin/gate` passes (including `cargo clippy -D warnings`, which will
      catch any malformed doc comments).

## Evidence
- All 28 top-level subcommand variants, plus the 2 nested `release-policy`
  and 3 nested `fleet` subcommands, now have `///` doc comments.
- Flag-level docs added for all 6 named commands (`run`, `synthesize`,
  `backfill`, `setup`, `fleet` — all 3 fleet subcommands — and
  `prepare-self-release`), plus the global `--error-format` flag that
  appears on every subcommand's help.
- Descriptions were written from direct knowledge of the code paths each
  flag feeds (verified against `run.rs`, `synthesis.rs`, `self_release.rs`,
  `setup_fleet/*.rs` this session), not invented — e.g. `--publish-release-body`
  is documented as "provider=github only" because `run_pipeline` gates it
  that way, `--confirm-release-body` on backfill is documented as required
  "alongside mode=release-body" matching the actual guard in `backfill`.
- Bonus (not in the original oracle): `landmark describe --json` derives its
  `inputs[].help` field from the same clap doc comments, so the agent-native
  self-description document is now populated for these commands/flags too —
  verified live via `describe --json | jq`.
- `cargo run --locked -- --help` and all 6 named `--help` invocations spot-
  checked for zero blank descriptions; `cargo clippy --locked --all-targets
  -- -D warnings` confirmed no malformed doc comments.

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
