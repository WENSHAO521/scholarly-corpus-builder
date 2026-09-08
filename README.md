# Scholarly Corpus Builder

Scholarly Corpus Builder is a provenance-aware Agent Skill for constructing
compact scholarly corpora and deriving reusable discipline, journal,
historical-scholar, and author-level writing profiles from metadata,
abstracts, lawful open-access text, public-domain material, and
user-authorized sources.

Its primary product is not a warehouse of papers. Its primary product is a
compact, reproducible, source-traceable representation of how a scholarly
community, journal, historical tradition, or individual author structures
academic writing.

## What it does

- Acquires the minimum lawful scholarly material needed to answer a specific
  style/structure question.
- Verifies and records provenance for every source used.
- Extracts sentence, paragraph, argument, evidence, section-architecture,
  claim-calibration, and intellectual-rhythm features.
- Assembles a structured, versioned, cacheable profile — not a raw corpus.
- Refreshes profiles incrementally instead of rebuilding from scratch.

## Why corpus profiles (not just "search and read")

Downstream writing systems (a voice engine, a journal-fit engine, a
book-writing workflow) repeatedly need to know "how does this journal/field/
scholar/author write?" Re-answering that from scratch every time is slow,
costly, and prone to inconsistent sampling. This skill produces a durable,
auditable answer once, and knows when that answer is still good enough to
reuse (see the Corpus Selection Gate in `references/refresh-policy.md`).

## Corpus types

| Type | Learns | Reference |
|---|---|---|
| Discipline | Current field-wide writing conventions | `references/discipline-profile.md` |
| Journal | One venue's observed writing architecture | `references/journal-profile.md` |
| Historical scholar | Transferable argument mechanics, not phrasing | `references/historical-profile.md` |
| Author | The user's own established voice | `references/author-profile.md` |

## Source hierarchy

```text
Tier 1  User-provided or explicitly authorized material
Tier 2  Open metadata (Crossref, OpenAlex, PubMed, repositories)
Tier 3  Open abstracts
Tier 4  Open-access full text (repositories, PMC, preprints, OA versions)
Tier 5  Public-domain historical works
```

Metadata-first, full-text-last. See `references/source-hierarchy.md`.

## Copyright boundary

No paywall bypass, no leaked/shadow-library sourcing, no unnecessary full-text
storage, no phrase-imitation libraries, no living-author imitation systems.
Full rules in `references/copyright-boundary.md`.

## How corpus selection works

Before retrieving anything new, the skill checks a Corpus Selection Gate:
`CURRENT`, `STALE`, `INSUFFICIENT`, `NEW_TARGET`, or
`USER_REQUESTED_REFRESH`. A `CURRENT` profile is reused rather than rebuilt.
See `references/refresh-policy.md`.

## Journal profiles

Empirical profiles of a sampled set of articles (typically 20-50, diversified
by year/type/subfield/author) — never presented as formal submission
requirements. See `references/journal-profile.md`.

## Discipline profiles

Field-wide conventions sampled across subfields and venues (typically 40-100
works). See `references/discipline-profile.md`.

## Historical profiles

Transferable argument architecture from historical scholars, sourced from
verified-or-likely public-domain material, without quotation banks or phrase
libraries. See `references/historical-profile.md`.

## Author profiles

The highest-personalization corpus type, built only from user-provided or
explicitly authorized works, with name-collision safeguards and an explicit
"do not preserve" list for errors and bad habits. See
`references/author-profile.md`.

## Caching and refresh

Profiles are versioned (e.g. `NatureMedicine-2026Q3`), refreshed
incrementally, and carry freshness defaults (12-24 months for disciplines,
6-12 months for journals, 3-6 months for fast-moving computing/AI venues, no
fixed schedule for historical or author profiles). See
`references/refresh-policy.md`.

## Integration

Designed to sit alongside, and stay decoupled from, an Adaptive Model Router,
a Scholarly Voice Engine, and a Journal Fit Engine. This skill decides *what*
to acquire and *what profile* results; it does not route models and does not
decide manuscript-journal fit. See `references/integration.md`.

## Evaluation

`evals/` contains fixtures covering source selection, metadata/abstract/
full-text sufficiency, copyright refusal, paywall handling, deduplication,
version resolution, journal/discipline sampling, historical/author corpus
handling, refresh decisions, profile staleness, and multilingual corpora.
Run `python scripts/validate_skill.py` to check repo integrity (required
files, frontmatter, JSONL validity, local markdown links, embedded JSON
schema examples).

## Limitations

- No guaranteed access to paywalled literature.
- No exhaustive bibliographic database — retrieval depends on host tools.
- Stylistic similarity to a journal's observed profile does not predict
  editorial acceptance.
- No automatic copyright or public-domain determination — status is recorded
  conservatively (`verified` / `likely` / `unknown`).
- A sampled profile is not a claim of exhaustive representativeness of an
  entire discipline.
- No direct living-author imitation, ever.

## Installation

Place this directory where your agent host discovers skills (e.g. a
`skills/` directory), keyed by the `name` field in `SKILL.md`'s frontmatter.
`agents/openai.yaml` provides an OpenAI-compatible agent config pointing at
the same instructions and reference files for hosts that consume that format.
