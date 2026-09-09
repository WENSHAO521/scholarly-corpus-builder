# Changelog

All notable changes to this skill are documented here.

## [Unreleased]

Working toward v1.0.0 per the roadmap below. Entries here are added as
milestones land; VERSION is not bumped until a real release is cut.

### Milestone: Source Adapter Layer (toward v0.2.0)

- Added `scb/` — a standard-library-first Python runtime package
  implementing the acquisition/resolution/analytics pipeline.
- `scb/records.py` — the Canonical Scholarly Record dataclass shape
  (identifiers, access, versions, provenance, conflicts).
- `scb/identifiers.py` — DOI/PMID/PMCID/arXiv/ISSN/ORCID normalization and
  EXACT/PROBABLE/AMBIGUOUS/UNRESOLVED identifier-match classification.
- `scb/dedup.py` — deduplication with the documented priority chain
  (identifier match → title+author+year → conservative fuzzy title
  review); never merges on title similarity alone.
- `scb/versions.py` — version resolution keeping
  `bibliographic_authority` and `best_lawful_access` as two independent,
  never-overwriting concepts.
- `scb/http_client.py` — shared HTTP engine: timeout, bounded retry,
  `Retry-After` handling, exponential backoff, and adapter state
  classification (AVAILABLE/DEGRADED/RATE_LIMITED/AUTH_REQUIRED/
  UNAVAILABLE). Standard library only, with an injectable transport so
  tests never touch the network.
- `scb/cache.py` — lightweight local file cache (`.cache/<adapter>/`),
  TTL-based, no database.
- `scb/adapters/` — seven adapters, each declaring only the capabilities
  it actually supports: OpenAlex, Crossref, PubMed (E-utilities), PMC,
  arXiv, DOAJ, and a local User File adapter (txt/md/html/xml/docx via
  the standard library; PDF requires an injected extractor — no OCR is
  implemented).
- 94 new offline unit tests (recorded/sanitized fixtures per adapter);
  full suite now 120 tests, all passing.
- **Live-verified** against real APIs during development (2026-09-09,
  not part of default CI): OpenAlex, Crossref, arXiv, PubMed, and DOAJ
  adapters confirmed working end-to-end against live responses for a
  real DOI/PMID/arXiv ID.
- **Real finding from live verification**: NCBI decommissioned the
  legacy per-article PMC OA Web Service (`oa.fcgi`) in August 2026,
  replacing it with bulk PMC Cloud Service (AWS S3) datasets — there is
  no longer a lightweight per-PMCID REST call for OA status/license/
  full-text pointers. The PMC adapter was redesigned around this: it now
  only performs PMID/PMCID/DOI cross-reference resolution via the
  current NCBI ID Converter API (live-verified), and honestly reports
  `access.is_oa = None` rather than guessing. OA/license resolution for
  PMC-hosted articles now relies on OpenAlex locations or Crossref
  license data instead (see the OA Resolver milestone).

### Milestone: OA Resolver, Sampling, Manifest, Acquisition Engine (v0.2.0 complete)

- `scb/oa_resolver.py` — resolves a canonical record to one of nine
  access states (`STRUCTURED_FULLTEXT_AVAILABLE` down to
  `RESOLUTION_FAILED`), ordered most-to-least actionable. Never probes a
  hidden publisher URL or fabricates a URL that wasn't actually present
  on the record.
- `scb/retrieval_depth.py` — LEVEL_0_METADATA .. LEVEL_3_FULLTEXT, and
  `meets_requested_depth()` used to filter candidates to the minimum
  level actually needed.
- `scb/sampling.py` — diversified sampling with author/year/issue
  dominance caps and backfill-to-target, plus the suggested size ranges
  from references/corpus-policy.md as `SUGGESTED_TARGETS`.
- `scb/manifest.py` — the corpus manifest schema with an explicit,
  threshold-based sufficiency gate (`COMPLETE` /
  `COMPLETE_WITH_LIMITATIONS` / `PARTIAL` / `INSUFFICIENT` / `FAILED`) —
  deliberately not an expensive convergence algorithm.
- `scb/acquisition.py` — the orchestrator: `CorpusRequest` →
  search-across-adapters → dedup → OA resolve → depth-filter → sample →
  manifest. One failing adapter never sinks the whole acquisition; its
  error is recorded and the manifest notes reduced source coverage as a
  known bias.
- 47 new tests (158 total, all passing). Two real bugs were caught and
  fixed by this milestone's tests before being committed: an OA-resolver
  state-precedence ordering bug (`RESOLUTION_FAILED` vs `LICENSE_UNKNOWN`
  for a record with no title) and a sampling-engine test that incorrectly
  asserted no dominance suppression while reusing a fixture with identical
  issue metadata across records.

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
