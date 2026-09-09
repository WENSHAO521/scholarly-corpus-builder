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

### Milestone: Measured Style Analytics + Corpus Stability (v0.3.0)

- `scb/text_normalize.py` — splits extracted text into sections with a
  normalized semantic role (`introduction`, `methods`, `results`, ...)
  where recognized, and `role="other"` with the original heading
  preserved verbatim where not — a humanities/law/philosophy document is
  never forced into IMRaD.
- `scb/analytics/` — sentence metrics (length distribution, IQR,
  variance, short/long share), paragraph metrics, lexical metrics
  (first-person/passive-voice/nominalization/hedge/certainty/transition
  rates per 1,000 words), citation metrics (author-date and
  numeric-bracket detection, density, sentence-final share,
  citation-free paragraph share), section-architecture metrics
  (word share per role, dedicated-limitations detection, contribution
  placement), a rule-based claim classifier (8 categories, fixed
  priority order, hedge co-occurrence), rule-based rhetorical-move
  detection (14 moves, multi-label per paragraph), and an intellectual-
  rhythm detector (a small named set of 2/3-gram sentence-role
  sequences, always reported at "low" confidence). Every classifier
  module's docstring states plainly that its output is an inferred
  heuristic label, not objective fact.
- `scb/profile_schema.py` — aggregates per-document analytics into the
  corpus-level StyleProfile schema from references/style-feature-schema.md,
  with sample-size-based confidence labeling and honest small-sample
  labels (`illustrative` / `limited` / `moderate` / `potentially_robust`).
- `scb/stability.py` — the Corpus Stability Engine: deterministic
  split-corpus comparison across five numeric features with an explicit
  35%-relative-difference tolerance (not a fitted statistical model),
  yielding `STABLE`/`MOSTLY_STABLE`/`UNSTABLE`/`INSUFFICIENT_SAMPLE`;
  plus a lightweight, reproducible (fixed-seed) bootstrap resampler for
  sentence-length spread, using only the standard library.
- 53 new tests (211 total, all passing), including a genuinely
  constructed "stable" and "unstable" synthetic corpus pair that
  exercises the split-test classifier end-to-end rather than only
  mocking it.
- Two more real bugs caught and fixed by these tests before commit: a
  text-normalizer heuristic that silently discarded multi-line reference
  lists sharing a paragraph block with their heading, and a causal-claim
  cue list that missed the bare verb form "cause" (only matched
  "causes"/"caused"/"causing").

### Milestone: Profile Builders + Author Voice Incremental Learning (v0.4.0)

- `scb/profiles/` — journal, discipline, historical-scholar, author, and
  book profile builders, each mapping the shared StyleProfile onto its
  corpus-type's schema from references/*.md. Fields that cannot yet be
  honestly derived (e.g. abstract-only architecture, cross-chapter
  concept recurrence) are explicitly left `[]`/"not_computed" rather
  than guessed. The historical-scholar builder never stores excerpt
  text — verified in tests that raw sentence content does not leak into
  its output.
- `scb/author_learning.py` — `merge_author_profile()` incrementally
  updates an existing author profile from newly added documents without
  needing the old documents again: numeric leaves are count-weighted
  and classified `stable`/`strengthening`/`weakening`/`new`/`uncertain`
  (uncertain below a 5-document confidence floor on either side), and
  `do_not_preserve` corrections carry forward rather than being
  silently dropped. `analyze_edit_diffs()` implements PART XXXV's
  edit-diff learning (comparing AI-draft vs. user-edited-final pairs
  for recurring sentence-length/hedging/first-person/transition
  tendencies) as a pure function — it stores no raw text and enables no
  persistence itself; that stays a caller/host decision.
- 16 new tests (227 total, all passing).

### Milestone: Profile Compiler + Cross-Skill Protocol (v0.5.0)

- `scb/compiler.py` — the Profile Compiler: turns a measured profile
  into policy statements tagged `OBSERVED` / `RECOMMENDED` / `MANDATORY`,
  where `MANDATORY` is only ever produced from a profile's own
  `do_not_preserve` corrections or caller-supplied official
  requirements — never invented from an observed pattern (tested
  explicitly: a journal's observed contribution-placement pattern always
  compiles to `OBSERVED`, never `MANDATORY`). Also builds the three
  standardized cross-skill output contracts from
  references/integration.md: `SCHOLARLY_PROFILE_V1`, `VOICE_CONTEXT_V1`,
  `JOURNAL_STYLE_CONTEXT_V1`.
- `scb/comparison.py` — profile comparison (shared traits vs. material
  differences, 25%-relative-difference threshold) and
  `author_vs_journal_adaptation()`, which is tested to never recommend
  imitating a journal's phrasing and always keeps "author's substantive
  argumentative voice" in `do_not_change`. `synthesize_composite_voice()`
  applies the author > discipline > journal > historical precedence
  from PART XXXVI without mechanically averaging the layers together.
- 20 new tests (238 total, all passing). One more real bug caught and
  fixed before commit: journal profiles deliberately expose only labels
  ("short"/"moderate"/"long") for sentence length and citation density
  rather than raw numbers (to avoid the fake-statistical-precision
  problem in PART LXXXI), but the comparison engine only knew how to
  diff raw numbers — so an author-vs-journal comparison silently found
  zero differences. Fixed by extracting the label-bucketing rule into a
  shared function (`scb/profile_schema.py: label_sentence_length` /
  `label_density`) that both the journal-profile builder and the
  comparison engine now use, so a raw number and a label can be compared
  honestly by label instead of either fabricating precision or silently
  comparing nothing.

### Milestone: CLI, Refresh Infrastructure, Offline Robustness (toward v0.6.0/v0.7.0)

- `scb/cli.py` — a developer CLI (`lookup`, `search`, `resolve-oa`,
  `validate`), JSON output throughout, not required for normal Skill
  usage. Live-verified end-to-end: `python -m scb.cli lookup --adapter
  crossref --doi 10.1371/journal.pone.0000308` against the real Crossref
  API.
- `scb/refresh.py` — code form of references/refresh-policy.md's Corpus
  Selection Gate (`CURRENT`/`AGING`/`STALE`/`INCOMPLETE`/`NEW_TARGET`/
  `USER_REQUESTED_REFRESH`) with the documented freshness windows
  (journal 6-12 months, fast-moving journal 3-6 months, discipline
  12-24 months, no periodic window for historical/author profiles), and
  `diff_profiles()` for the stable/changed/newly-observed refresh diff,
  built on top of the existing comparison engine rather than
  duplicating its logic.
- 12 new offline failure-handling tests (`tests/test_failure_handling.py`,
  PART XCI): every adapter's lookup methods return `None` rather than
  raising on a 404; a persistent 429/503 exhausts the bounded retry
  policy and then surfaces instead of hanging or fabricating a result;
  malformed JSON/XML responses raise instead of silently producing a
  wrong record; empty result sets return an empty list, not an error;
  and acquisition completes with a partial manifest when some adapters
  are down. CI remains fully offline — no test depends on live API
  uptime.
- 28 new tests total (266 total, all passing).

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
