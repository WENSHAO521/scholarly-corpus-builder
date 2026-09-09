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

**[ARCHITECTURE.html](ARCHITECTURE.html)** — open in a browser for a visual
pipeline diagram (request → gate → adapters → resolution → sampling →
analytics → profiles → compiler → downstream skills) and the guarantees each
stage actually enforces.

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
| Book | Chapter-level structure of a monograph, analyzed on its own terms | `scb/profiles/book.py` |

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

## Runtime engine (`scb/`)

A standard-library-first Python package implementing the acquisition →
resolution → analytics → profiling → compilation pipeline in code:

- **Source adapters**: OpenAlex, Crossref, PubMed, PMC, arXiv, DOAJ, and a
  local User File adapter (txt/md/html/xml/docx; PDF needs a host-supplied
  extractor — no OCR). Each declares only the capabilities it actually
  supports and is live-verified against the real APIs (see CHANGELOG).
- **Resolution**: identifier normalization/matching, deduplication (never
  merges on title similarity alone), version resolution
  (`bibliographic_authority` vs. `best_lawful_access` kept independent),
  and an OA resolver that never probes a hidden URL or fabricates one.
- **Acquisition**: a diversified sampling engine (author/year/issue
  dominance caps), an explicit corpus-manifest sufficiency gate, and an
  orchestrator where one failing adapter never sinks the whole run.
- **Analytics**: measured sentence/paragraph/lexical/citation/section
  metrics, plus rule-based claim/rhetorical-move/intellectual-rhythm
  classifiers whose every output is explicitly labeled inferred, not fact.
- **Stability**: a corpus stability engine that actually runs a
  deterministic split-corpus comparison and a reproducible bootstrap
  resampler — a profile is never trusted just because a corpus exists.
- **Profiles & compiler**: journal/discipline/historical/author/book
  profile builders matching `references/*.md`; incremental author-profile
  learning and edit-diff learning; a Profile Compiler that keeps
  `OBSERVED`/`RECOMMENDED`/`MANDATORY` strictly distinct and emits the
  three cross-skill protocols (`SCHOLARLY_PROFILE_V1`,
  `VOICE_CONTEXT_V1`, `JOURNAL_STYLE_CONTEXT_V1`); a comparison engine
  for journal-vs-journal, era-vs-era, and author-vs-journal adaptation
  (never recommending imitation of a journal's phrasing).
- **Refresh**: a code form of the Corpus Selection Gate and freshness
  windows below, reusing the comparison engine for refresh diffs.

A developer CLI (`python -m scb.cli --help`) wraps this for manual
lookup/search/OA-resolution/validation — JSON output, not required for
normal Skill use.

## Evaluation

`evals/` contains 113 fixtures covering source selection, metadata/abstract/
full-text sufficiency, copyright refusal, paywall handling, deduplication,
version resolution, journal/discipline sampling, historical/author corpus
handling, refresh decisions, profile staleness, multilingual corpora, OA
resolution, analytics honesty (measured vs. inferred), compiler safety
(OBSERVED/RECOMMENDED/MANDATORY), cross-skill protocols, and offline
failure handling. Run `python scripts/validate_skill.py` to check repo
integrity (required files, frontmatter, JSONL validity, local markdown
links, embedded JSON schema examples, and that the `scb/` package parses).
Run `python -m unittest discover -s tests -v` for the full test suite
(unit + offline adapter/failure-handling tests).

## Installation

> **`SKILL.md`'s instructions are fully usable without Python** — a host
> with no Python execution can still follow the policy directly (source
> hierarchy, retrieval minimization, copyright boundary, profile
> schemas). Where the host *does* provide Python, the Skill prefers its
> bundled `scb/` runtime engine (adapters, resolution, analytics,
> stability, profile builders, compiler — see "Runtime engine" below)
> over ad hoc scraping, since it already implements this policy in
> tested code. Python is also needed for development, validation,
> testing, packaging, and CI regardless of which path a given run takes.

Repository: `https://github.com/WENSHAO521/scholarly-corpus-builder`

### Runtime vs development install

This repository has two shapes:

- **Development repository** (this repo, cloned via git) — includes
  `tests/`, `evals/`, `scripts/`, and `.github/`. Useful if you want to
  modify the Skill, run its validator, or build a release.
- **Runtime package** — a minimal, frozen ZIP built by
  `scripts/package_runtime.py`, containing `SKILL.md`, `README.md`,
  `LICENSE`, `VERSION`, `agents/openai.yaml`, `references/`, and the
  `scb/` Python package (adapters, resolution, analytics, stability,
  profile builders, compiler). This is what an Agent Skill host needs
  to both load the Skill's instructions and, where Python is available,
  run its bundled engine.

Either shape works as a Skill install, since a host only reads `SKILL.md`
and the files it references — but the runtime package is smaller and
avoids exposing development tooling to the host.

### Option A — git clone (rolling development)

macOS/Linux — verify the skills directory your host expects against its
current documentation; a commonly used layout is `$HOME/.agents/skills`:

```bash
mkdir -p "$HOME/.agents/skills"

git clone https://github.com/WENSHAO521/scholarly-corpus-builder.git \
  "$HOME/.agents/skills/scholarly-corpus-builder"
```

Windows PowerShell:

```powershell
$skillsDir = Join-Path $HOME ".agents\skills"

New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null

git clone https://github.com/WENSHAO521/scholarly-corpus-builder.git `
  (Join-Path $skillsDir "scholarly-corpus-builder")
```

`main`/`master` is rolling development — see Option B for a reproducible,
tagged install.

### Option B — stable, tagged release (reproducible)

Once a version tag exists (e.g. `v0.1.1`):

```bash
git clone \
  --branch v0.1.1 \
  --depth 1 \
  https://github.com/WENSHAO521/scholarly-corpus-builder.git \
  scholarly-corpus-builder
```

(No `v0.1.1` tag has been published yet as of this writing — Option A/C
apply until the first tag exists.)

`main` = rolling development. A version tag = a reproducible, released
snapshot. Prefer a tag when you want stability.

### Option C — runtime ZIP (no git required)

1. Download the release ZIP (`scholarly-corpus-builder-vX.Y.Z.zip`) and its
   `.sha256` file from the repository's Releases page.
2. Optionally verify the checksum:
   - macOS/Linux: `sha256sum -c scholarly-corpus-builder-vX.Y.Z.zip.sha256`
   - Windows PowerShell: `Get-FileHash .\scholarly-corpus-builder-vX.Y.Z.zip -Algorithm SHA256`
     and compare against the `.sha256` file's contents.
3. Extract the ZIP.
4. Copy the **inner** `scholarly-corpus-builder/` folder (not the ZIP file
   itself) into your host's Skill directory.

The final path must look like:

```text
.../skills/scholarly-corpus-builder/SKILL.md
```

**Not** double-nested like this:

```text
.../skills/scholarly-corpus-builder/scholarly-corpus-builder/SKILL.md
```

(The ZIP itself is built with exactly one root folder, so double-nesting
only happens if you copy the extracted folder into a same-named folder you
already created — extract directly into the host's skills directory.)

### Verify installation

- Confirm your host actually discovers the Skill (mechanism varies by
  host — check its skill-listing command or UI).
- Confirm the Skill name shown is exactly `scholarly-corpus-builder`
  (from `SKILL.md`'s frontmatter).
- Confirm `SKILL.md` sits directly inside the `scholarly-corpus-builder/`
  folder your host scans — not nested one level deeper.
- Confirm there is only one install of this Skill on the path your host
  scans (a stray copy from a failed earlier install can shadow or conflict
  with the current one).
- If your host supports explicit invocation syntax (e.g. a slash command),
  verify the exact syntax against that host's own documentation before
  relying on it — invocation conventions differ by host and are not
  standardized by this Skill.

### Updating (git installs)

```bash
git -C "<skill-directory>/scholarly-corpus-builder" status
git -C "<skill-directory>/scholarly-corpus-builder" pull --ff-only
```

Check `status` first so you notice any local modifications before pulling.
`pull --ff-only` fails loudly instead of silently merging or discarding
your changes — do not reach for `git reset --hard` as a default update
method; investigate first if a fast-forward pull is rejected.

### Development

The development repository additionally includes:

```text
scb/                           the runtime engine (adapters, resolution, analytics, profiles, compiler)
scripts/validate_skill.py    source and runtime validator
scripts/package_runtime.py   deterministic runtime ZIP packager
tests/                        standard-library unittest suite (284 tests)
.github/workflows/validate.yml     CI: offline validation + tests on every push/PR
.github/workflows/release.yml      tag-driven release (vX.Y.Z tags only)
.github/workflows/live-check.yml   manual-only smoke test against real scholarly
                                    APIs (workflow_dispatch) — informational, never
                                    blocks a merge or release; this is how the
                                    OpenAlex/PMC API drift in CHANGELOG was found
```

### Validation

```bash
python scripts/validate_skill.py                                  # source mode (default)
python scripts/validate_skill.py --mode runtime --root <dir>       # validate an extracted runtime package
python -m unittest discover -s tests -v                            # run the test suite
```

Source mode checks the full development repository (required files,
`SKILL.md` frontmatter, JSONL eval fixtures, local Markdown links, embedded
JSON schema examples, and that `references/` matches the runtime allowlist).
Runtime mode checks only what a Skill host needs, and additionally rejects
any development file (`tests/`, `evals/`, `scripts/`, `.github/`, `.git/`,
secrets) found inside the tree being validated.

### Release packaging

```bash
python scripts/package_runtime.py
```

Builds `dist/scholarly-corpus-builder-vX.Y.Z.zip` (version read from
`VERSION`) using an explicit file allowlist, writes a `.sha256` checksum
alongside it, and self-validates the built package by extracting it to a
temporary directory and re-running the runtime validator against it —
packaging fails loudly if that validation fails. `dist/` is git-ignored;
built ZIPs are release artifacts, not repository content.

Releases are cut by pushing a `vX.Y.Z` tag matching `VERSION`; the release
workflow refuses to publish if the tag and `VERSION` disagree, or if
validation/tests/packaging fail. See `RELEASE_CHECKLIST.md`.

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
- PMC's per-article OA lookup was decommissioned by NCBI in August 2026
  (see CHANGELOG); the PMC adapter now only does identifier
  cross-referencing, and OA status for PMC-hosted articles relies on
  OpenAlex/Crossref instead. External APIs evolve — correctness here is
  as verified on the dates noted in CHANGELOG, not a permanent guarantee.
- Claim/rhetorical-move/intellectual-rhythm classification is rule-based
  keyword-cue matching, not NLP/ML — every such output is explicitly
  labeled an inferred heuristic, never presented as objective fact.
- No systematic, human-QA'd, cross-disciplinary benchmark across many
  fields has been run — one real end-to-end acquisition (live OpenAlex
  data, public administration) is documented in CHANGELOG as a genuine
  but small-scale demonstration, not a validated benchmark.
- No Voice Engine A/B comparison — the Scholarly Voice Engine this skill
  is designed to feed does not exist in this repository to test against.
- Eval suite is 113 fixtures, short of a 150+ target; growth stopped at
  genuinely new scenarios rather than padding to hit a number.
