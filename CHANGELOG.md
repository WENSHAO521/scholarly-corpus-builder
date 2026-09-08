# Changelog

All notable changes to this skill are documented here.

## [0.1.1] - 2026-09-09

Release, testing, runtime packaging, and CI hardening. No corpus policy,
schema, or eval-fixture content changed — this release is engineering
hardening, not a conceptual redesign.

### Added

- `VERSION` file as the single canonical source of the package version.
- Source and runtime validation modes in `scripts/validate_skill.py`
  (`--mode source` / `--mode runtime --root <dir>`), sharing one set of
  checks instead of duplicating validator logic. Runtime mode additionally
  rejects development files (`tests/`, `evals/`, `scripts/`, `.github/`,
  `.git/`, secrets) found inside the tree being validated.
- `scripts/package_runtime.py` — deterministic, allowlist-based runtime ZIP
  packager (standard library only). Produces
  `dist/scholarly-corpus-builder-vX.Y.Z.zip` plus a `.sha256` checksum and a
  `release-manifest.json` inside the package, and self-validates the built
  archive by extracting it and re-running runtime validation against it.
- Standard-library `unittest` suite (`tests/test_validate_skill.py`,
  `tests/test_package_runtime.py`, 26 tests) covering validator positive/
  negative paths and packaging correctness, including a reproducible-build
  (identical SHA-256 across separate build directories) test.
- `.github/workflows/validate.yml` — runs on every push/PR: source
  validation, unit tests, runtime package build, and runtime package
  validation, with `contents: read` permissions only.
- `.github/workflows/release.yml` — runs only on `vX.Y.Z` tags: verifies the
  tag matches `VERSION`, re-runs validation/tests/packaging, verifies the
  checksum, and attaches the runtime ZIP and checksum to a GitHub Release.
  Refuses to publish if any step fails or the tag disagrees with `VERSION`.
- `.gitignore` (excludes `dist/`, `__pycache__/`, and other build/OS/editor
  artifacts — built packages are release artifacts, never repository
  content).
- `RELEASE_CHECKLIST.md` — maintainer-facing pre-tag checklist (not part of
  the runtime package).
- Expanded `README.md` installation documentation: runtime-vs-development
  install, git clone (rolling and tagged), runtime ZIP install with
  double-nesting warning, installation verification, update instructions,
  development/validation/packaging workflow, and an explicit "Python is not
  required to use this Skill" statement.

### Changed

- `scripts/validate_skill.py`'s local-Markdown-link check now reports a
  broken link as an error (previously a warning) — every local link must
  resolve.

### Unchanged (by design)

- `SKILL.md` corpus policy, source hierarchy, copyright boundary, and all
  four profile schemas.
- All 48 existing evaluation fixtures.

### Roadmap (not yet implemented)

- v0.2.0 — source adapter layer (OpenAlex/Crossref/PubMed/PMC/arXiv), open-
  access resolver, corpus manifest, real-world corpus acquisition tests.

## [0.1.0] - 2026-09-09

### Added

- Initial release of the `scholarly-corpus-builder` skill.
- Core `SKILL.md` covering scope, source hierarchy, retrieval minimization,
  copyright boundary, corpus selection gate, profile outputs, and
  integration rules.
- Four corpus types: discipline, journal, historical scholar, author.
- Reference documentation: corpus policy, source hierarchy, provenance
  schema, style-feature schema, journal/discipline/historical/author profile
  schemas, copyright boundary, refresh policy, integration.
- Provenance schema with verification states (`VERIFIED`,
  `PARTIALLY_VERIFIED`, `NEEDS_CHECK`, `REJECTED`) and honest build-record
  tracking (attempted/retrieved/usable/rejected).
- Corpus Selection Gate (`CURRENT` / `STALE` / `INSUFFICIENT` / `NEW_TARGET` /
  `USER_REQUESTED_REFRESH`) and freshness defaults per corpus type.
- 48 evaluation fixtures across 5 files covering source selection, metadata/
  abstract/full-text sufficiency, copyright refusal, paywall handling,
  deduplication, version resolution, journal/discipline sampling, historical/
  author corpus handling, refresh decisions, profile staleness, and
  multilingual corpora.
- Standard-library-only validator (`scripts/validate_skill.py`).
- `agents/openai.yaml` for OpenAI-compatible hosts.

### Roadmap (not yet implemented)

- v0.2 — structured source adapters and concrete caching implementation.
- v0.3 — journal profile refresh automation and comparison mode tooling.
- v0.4 — author profile differential learning across successive uploads.
- v0.5 — cross-language corpus analytics.
