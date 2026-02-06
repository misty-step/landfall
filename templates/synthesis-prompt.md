You are preparing product release notes for **{{PRODUCT_NAME}}** version **{{VERSION}}**.

Convert the technical changelog into concise, benefit-focused notes for end users.

Requirements:
- Use clear, user-facing language.
- Group output with these exact headings (omit empty sections):
  - `## New Features`
  - `## Improvements`
  - `## Bug Fixes`
- Focus on impact: what changed for users and why it matters.
- Skip internal-only changes such as CI, tooling, refactors, or dependency bumps unless directly user-visible.
- Do not mention commit hashes, PR numbers, or internal workflow details.
- Keep each bullet to one short sentence.

Technical changelog source:

{{TECHNICAL_CHANGELOG}}
