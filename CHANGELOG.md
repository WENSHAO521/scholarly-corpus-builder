# Changelog

All notable changes to this skill are documented here.

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
