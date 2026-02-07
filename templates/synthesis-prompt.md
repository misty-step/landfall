You are writing release notes for **{{PRODUCT_NAME}}** version **{{VERSION}}**.

Rewrite the technical changelog into concise, user-facing notes.

Rules:
- Use plain language and focus on user impact.
- Keep each bullet to one short sentence.
- Omit internal-only items (CI, tooling, refactors, dependency bumps) unless user-visible.
- Never include PR numbers, commit hashes, issue IDs, or internal process details.
- Keep the output tight: usually 3-7 bullets total.

Output format:
- Use only these section headings and this order (omit empty sections):
  - `## New Features`
  - `## Improvements`
  - `## Bug Fixes`
- Do not add any intro or outro text.

Few-shot examples:

Technical changelog:
### Features
- add one-click workspace import command
### Bug Fixes
- retry webhook processing when signatures expire
### Chores
- bump CI cache key

Expected release notes:
## New Features
- Added one-click workspace import to reduce setup time.

## Bug Fixes
- Webhook processing now retries after expired signatures to reduce failed deliveries.

Technical changelog:
### Bug Fixes
- fix dashboard crash when saving empty profile fields
### Refactor
- split parser module into smaller files

Expected release notes:
## Bug Fixes
- Fixed a dashboard crash that occurred when saving empty profile fields.

Technical changelog source:

{{TECHNICAL_CHANGELOG}}
