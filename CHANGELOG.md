# [1.3.0](https://github.com/misty-step/landfall/compare/v1.2.0...v1.3.0) (2026-02-09)


### Features

* generate portable release notes artifacts ([#26](https://github.com/misty-step/landfall/issues/26)) ([d4ca901](https://github.com/misty-step/landfall/commit/d4ca90199c4b022407ee8ba2705d2a385100356f)), closes [#7](https://github.com/misty-step/landfall/issues/7)

# [1.2.0](https://github.com/misty-step/landfall/compare/v1.1.5...v1.2.0) (2026-02-09)


### Features

* alert and signal synthesis failures ([#25](https://github.com/misty-step/landfall/issues/25)) ([8398ca0](https://github.com/misty-step/landfall/commit/8398ca066c51c45a025adff1e536c0bbdf2d5202))

## [1.1.5](https://github.com/misty-step/landfall/compare/v1.1.4...v1.1.5) (2026-02-09)


### Bug Fixes

* remove unused @semantic-release/npm dependency ([#24](https://github.com/misty-step/landfall/issues/24)) ([a353646](https://github.com/misty-step/landfall/commit/a353646e21c3381e440536e1c3ab3435dbeb3959)), closes [#5](https://github.com/misty-step/landfall/issues/5)

## [1.1.4](https://github.com/misty-step/landfall/compare/v1.1.3...v1.1.4) (2026-02-09)


### Bug Fixes

* harden self-release notes pipeline ([#23](https://github.com/misty-step/landfall/issues/23)) ([0a030b4](https://github.com/misty-step/landfall/commit/0a030b4c21e88daf5b5d68fd75cae2b83ce9938f))

## [1.1.3](https://github.com/misty-step/landfall/compare/v1.1.2...v1.1.3) (2026-02-08)


### Bug Fixes

* remove dead backward-compat code and warn on insecure API URLs ([#20](https://github.com/misty-step/landfall/issues/20)) ([0df6c21](https://github.com/misty-step/landfall/commit/0df6c21d601c60e71c25a86184b4ac67499535d4)), closes [#3](https://github.com/misty-step/landfall/issues/3) [#4](https://github.com/misty-step/landfall/issues/4)

## [1.1.2](https://github.com/misty-step/landfall/compare/v1.1.1...v1.1.2) (2026-02-08)


### Bug Fixes

* provider-agnostic LLM inputs for release synthesis ([#19](https://github.com/misty-step/landfall/issues/19)) ([451db2a](https://github.com/misty-step/landfall/commit/451db2a01256030bedd0039396af86e6f6a5ac03)), closes [#4](https://github.com/misty-step/landfall/issues/4)

## [1.1.1](https://github.com/misty-step/landfall/compare/v1.1.0...v1.1.1) (2026-02-08)


### Bug Fixes

* remove npm plugin and package.json references for non-Node project support ([#17](https://github.com/misty-step/landfall/issues/17)) ([c5e9dc0](https://github.com/misty-step/landfall/commit/c5e9dc0257622fff7914ac2db49732d764c39296)), closes [misty-step/vox#178](https://github.com/misty-step/vox/issues/178)

# [1.1.0](https://github.com/misty-step/landfall/compare/v1.0.0...v1.1.0) (2026-02-08)


### Bug Fixes

* harden release workflow template (concurrency, timeout, docs) ([#2](https://github.com/misty-step/landfall/issues/2)) ([228f57f](https://github.com/misty-step/landfall/commit/228f57f67cb93db2d7b4d9ebfed6a4a485f330e3))


### Features

* integrate Landfall release pipeline ([#1](https://github.com/misty-step/landfall/issues/1)) ([2d36967](https://github.com/misty-step/landfall/commit/2d36967ac612d228fa03905bc664cc4af74cd1d1))

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
- Switched Landfall self-release workflow to local `uses: ./` with OpenRouter input and strict synthesis checks.
- Added automatic major tag sync (`v1` -> latest release tag) in the self-release workflow.
- Removed deprecated `moonshot-*` action inputs in favor of `llm-*` provider-agnostic inputs.
