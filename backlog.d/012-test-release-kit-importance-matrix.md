# Pin release_kit's importance/audience/rich-artifact decision matrix with unit tests

Priority: P1 · Status: ready · Estimate: S

## Goal
`crates/landmark/src/release_kit.rs` (990 lines) has zero `#[test]` functions
covering `release_kit_importance`, `release_kit_audiences`,
`release_kit_needs_rich_artifacts`, or `release_kit_importance_reason` — the
functions that decide which final-mile artifacts (migration guides, docs
patches, blog drafts, demo videos) get planned for a release. Add direct unit
tests pinning the existing decision table so it can't silently drift.

## Oracle
- [ ] `release_kit_importance` (`release_kit.rs:438-456`) has a test per
      branch: `security` (classification.security), `migration` (major bump,
      or classification.breaking, or migration_heavy), `high`
      (significance == "high"), `launch` (empty latest_tag + bump != "none"),
      `low` (significance == "low"), and the `medium` fallback — constructed
      directly from `ReleaseClassification`/`RunVersionDecision` values, not
      through the full `plan()` pipeline.
- [ ] `release_kit_audiences` (`release_kit.rs:458-467`) has a test proving
      `release-operator`/`docs-owner` are added only when
      `release_kit_needs_rich_artifacts(importance)` is true, and the primary
      audience plus `developer-operator` are always present.
- [ ] `release_kit_needs_rich_artifacts` (`release_kit.rs:469`) has a test
      naming every importance value it treats as needing rich artifacts vs not.
- [ ] `cargo test --locked` and `bin/gate` pass.

## Notes
Verified live: `grep -rn "fn.*release_kit\|#\[test\]" crates/landmark/src/release_kit.rs`
shows no test functions, and `cargo test --locked release_kit` runs 0 tests.
The only existing coverage is `release_kit::assert_contract` inside replay
scenarios, which checks JSON *shape*, not that `importance`/`audiences` are
*correct* for a given classification/decision input. This ticket is
independent of `011-fix-release-kit-classifier-call-site.md` — it unit-tests
the pure decision functions directly with constructed inputs, so it can land
before, after, or alongside 011 without conflict.

**Why:** teardown report flagged release-kit as the highest-leverage untested
surface once classification correctness is addressed; this closes the "zero
unit tests on a 990-line decision module" gap independently confirmed by
running `cargo test --locked release_kit` (0 tests) during this groom pass.
