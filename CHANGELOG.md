# Changelog

All notable changes to Landfall are documented in this file.

The format is based on Keep a Changelog and uses Semantic Versioning.

## [Unreleased]

### Added
- Unit test coverage for synthesis and release update scripts.
- CI workflow for linting, tests, and `action.yml` schema validation.
- Example consumer release workflow template under `examples/release.yml`.

### Changed
- Hardened HTTP handling in synthesis and release update scripts with retries.
- Added structured logging and CLI input validation for Python scripts.
- Improved synthesis prompt guidance for concise, user-friendly release notes.
- Made synthesis and release-note update failures non-blocking in the composite action.
