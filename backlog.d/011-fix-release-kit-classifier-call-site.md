# Fix release_kit::plan's classifier call site to use structured commit data

Priority: P0 · Status: ready · Estimate: M

## Goal
`release_kit::plan` (`crates/landmark/src/release_kit.rs:173`) still calls the
plain-text substring classifier (`classify_release_context`, the
`classify_release_context_from_text` path) instead of the structured,
model-native classifier (`classify_release_context_with_deterministic` /
`classify_release_context_with_model`) that `synthesis.rs` already switched to.
Fix the call site so release-kit importance/audience planning is driven by
parsed commit data, closing the same misfire class the classifier fix already
closed for synthesis.

## Oracle
- [ ] `release_kit::plan` builds a `DeterministicReleaseContext`/`Vec<ContextCommit>`
      from `release.commits` (using the existing `classify_commit` parser for
      `conventional_type`/`breaking`, mirroring how `synthesis.rs` builds its
      deterministic context) and passes it to
      `classify_release_context_with_deterministic` (or `_with_model` where a
      model is configured), not the bare-text `classify_release_context`.
- [ ] A regression test reproduces the exact landmark v1.25.0 shape already
      pinned in `crates/landmark/src/classification_tests.rs` (commits:
      `feat(fleet): deliver backfill-first adoption lane`,
      `feat(run): emit release kit artifact graph`,
      `fix(fleet): attach to existing release workflows`, rendered as
      `### Features` / `### Bug Fixes` semantic-release headers) but exercised
      through `release_kit::plan`, and asserts `importance` is NOT `"low"` and
      `release_kit_needs_rich_artifacts` behaves accordingly.
- [ ] `cargo test --locked` and `bin/gate` pass.

## Notes
Verified live in `crates/landmark/src/release_kit.rs:150-174`: `release.commits`
(type `Vec<RunCommit>` with `subject`/`short_hash`/`body`,
`crates/landmark/src/release_ops/models.rs:252`) is already available at the
call site, so building the deterministic commit list is a small adapter, not a
redesign. `release_kit_importance` (`release_kit.rs:438-456`) directly branches
on `classification.significance`/`.security`/`.breaking`/`.migration_heavy`,
and a "low" significance from the substring classifier's landmine bugs (e.g.
`lower.contains("cli")` matching "reconcile", `"manifest"`/`"configuration"`
false-escalating, or simply missing `### Features`-style semantic-release
headers) silently shrinks the planned final-mile artifact set
(`release_kit_needs_rich_artifacts`, `release_kit.rs:469`) for what may be an
important release — the same failure shape as the groom teardown's headline
finding (`.factory-lanes/groom/landmark.md` §1), just in the kit-planning path
instead of the synthesis-skip path that was already fixed tonight (PR series
ending in commit `f7e122e`). This ticket closes the second call site.

**Why:** teardown finding §1 was fixed for `synthesis.rs` but `release_kit.rs`
was missed — confirmed live via `grep -rn "classify_release_context(" crates/landmark/src`,
which shows `release_kit.rs:173` is the only remaining caller of the unstructured
text classifier outside its own definition and tests.
