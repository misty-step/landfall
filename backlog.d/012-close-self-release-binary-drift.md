# Close self-release binary drift

Priority: P0 · Status: pending · Estimate: M

## Goal
Ensure Landfall self-release cannot publish version metadata that leaves the checked-in Linux action binary behind the Rust source.

## Oracle
- [ ] The self-release PR path updates `dist/landfall` and `dist/landfall.sha256` whenever `crates/landfall/Cargo.toml` changes.
- [ ] CI compares `target/x86_64-unknown-linux-musl/release/landfall` to `dist/landfall`, matching local `bin/gate`.
- [ ] A replay or unit test proves a generated self-release PR includes the binary artifact or fails with an actionable error.
- [ ] `bin/gate` exits 0 immediately after a self-release version bump.

## Children
1. Decide whether `prepare-self-release` should build the Linux binary directly or fail with a release-blocking instruction when the artifact is stale.
2. Add the binary `cmp` check to `.github/workflows/ci.yml` so hosted Quality Checks catch the same drift as `bin/gate`.
3. Extend `self_release_pr_path` replay evidence to assert binary/checksum handling.
4. Backfill the current `v1.18.1` binary/checksum alignment as a mechanical artifact update.

## Notes
- Evidence: after `chore(release): 1.18.1`, `bin/gate` failed at `cmp target/x86_64-unknown-linux-musl/release/landfall dist/landfall` while hosted Quality Checks had passed.
- Evidence: `.github/workflows/ci.yml` currently runs `cargo build`, `shasum -a 256 -c dist/landfall.sha256`, and `dist/landfall --help`, but does not compare the fresh build to the checked-in binary.
- Why: the groom harness audit found a gap between local and hosted verification on the artifact that consumers actually execute.

