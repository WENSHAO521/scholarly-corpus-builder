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

## Installation

> **Python is not required to use Scholarly Corpus Builder as an Agent
> Skill.** Python is needed only for development, validation, testing,
> packaging, and CI — never to run the Skill itself.

Repository: `https://github.com/WENSHAO521/scholarly-corpus-builder`

### Runtime vs development install

This repository has two shapes:

- **Development repository** (this repo, cloned via git) — includes
  `tests/`, `evals/`, `scripts/`, and `.github/`. Useful if you want to
  modify the Skill, run its validator, or build a release.
- **Runtime package** — a minimal, frozen ZIP built by
  `scripts/package_runtime.py`, containing only `SKILL.md`, `README.md`,
  `LICENSE`, `VERSION`, `agents/openai.yaml`, and `references/`. This is
  what an Agent Skill host actually needs to load the Skill.

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
scripts/validate_skill.py    source and runtime validator
scripts/package_runtime.py   deterministic runtime ZIP packager
tests/                        standard-library unittest suite
.github/workflows/            CI (validation + tagged release)
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
- No live source adapters yet (OpenAlex/Crossref/PubMed/PMC/arXiv), no open-
  access resolver, and no real-world corpus benchmark — this release is
  policy, schemas, and engineering hardening only; acquisition adapters are
  planned for v0.2.0.
