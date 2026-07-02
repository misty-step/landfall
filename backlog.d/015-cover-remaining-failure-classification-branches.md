# Cover the remaining classify_failure branches with tests

Priority: P2 · Status: ready · Estimate: S

## Goal
`classify_failure` (`crates/landmark/src/errors.rs:26-104`) is the function
behind every `--error-format json` failure envelope's `code`/`stage`/
`retryable`/`user_action` fields — an explicitly agent-native contract
(`docs/agent-integration.md` documents it directly). Only 2 of its 10 branches
have a pinned test today.

## Oracle
- [ ] A test exists for each remaining branch of `classify_failure`:
      `provider_outage` (429/rate-limit/timeout), `budget_skip`
      (budget/model.policy=off), `synthesis_degradation`
      (degraded/quality), `publication_mutation_failure` (release
      body/publish-release-body), `feed_failure` (rss/feed),
      `artifact_write_failure` (write/file/permission), `invalid_input`
      (unsupported provider/requires/must), and the `command_failed`
      catch-all for a message matching none of the above.
- [ ] Each test asserts `code`, `stage`, and `retryable` (not just that a
      match occurred) so silent branch reordering or overlap regressions get
      caught.
- [ ] `cargo test --locked` and `bin/gate` pass.

## Notes
Verified live: `grep -rn "classify_failure" crates/landmark/src` shows only
two call sites in `crates/landmark/src/tests.rs` (`--publish-release-body
requires --github-token` and `manifest changelog.source must be auto`),
covering `provider_auth` and `invalid_changelog_source` only. The function's
branch order matters (it's a first-match `if`/`else if` chain over
substring checks on a lowercased message), so untested branches are exactly
where an added/reordered branch could silently steal matches from another
without any test failing.

**Why:** confirmed by direct `grep` during this groom pass; not called out in
the teardown report, which focused on classification/version-decision rather
than the failure-envelope taxonomy.
