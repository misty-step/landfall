# Build the release-kit artifact graph

Priority: P1 · Status: done · Estimate: L

## Goal
Make Landmark emit a typed release-kit plan that recommends and tracks final-mile
release artifacts beyond changelogs, release notes, and version numbers while
keeping rich production behind explicit producer adapters.

## Oracle
- [x] `landmark run --dry-run` can write or print a `release-kit` artifact that
      validates against `schemas/release-kit.v1.schema.json`.
- [x] The kit distinguishes Landmark-owned outputs from adapter-owned outputs
      such as docs patches, blog drafts, images, GIFs, and demo videos.
- [x] Each planned artifact includes audience, owner, status, acceptance checks,
      provenance, and approval/blocker state.
- [x] Producer contracts name their adapter kind, inputs, outputs, mutation
      policy, command or handoff path, and evidence path.
- [x] Replay coverage proves a high-importance release plans richer artifacts
      while a low-importance/internal release keeps the kit small.

## Notes
- Landmark owns release truth, artifact planning, provenance, approvals, and
  evidence. It should not become a media renderer, brand studio, or CMS engine.
- Start from the current release context packet and run evidence model. Extend
  typed artifacts before adding any producer-specific integration.
- Producer adapters may be local CLIs, browser automation, remote services,
  harness skills, or human approval lanes.

## Delivered
- Added runtime release-kit planning to `landmark run`, embedding a schema-valid
  `release_kit` in stdout evidence and writing `.landmark/run/release-kit.json`
  for normal runs.
- Extended run evidence with release-kit path, schema, and hash metadata.
- Planned Landmark-owned changelog/notes/feed outputs separately from
  producer-adapter migration guide, docs update, blog draft, and demo video
  handoffs.
- Required producer contract `command` and `evidence_path` in the release-kit
  schema and replay validation.
- Extended replay coverage for dry-run printing, normal file writes,
  high-importance richer artifact graphs, and low internal small kits.
- Verified with focused replay scenarios, schema-backed replay checks, fresh
  critic re-review, and `bin/gate`.
