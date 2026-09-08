# Release Checklist

This file is a development-repository checklist. It is intentionally not
part of the runtime package (see `references/copyright-boundary.md` and
`README.md` § Runtime vs development install for why the runtime package
stays minimal).

Before tagging a release:

- [ ] `VERSION` updated to the new version (no leading `v`)
- [ ] `CHANGELOG.md` updated with a dated entry for the new version
- [ ] `python scripts/validate_skill.py` (source mode) passes with 0 errors
- [ ] `python -m unittest discover -s tests -v` passes
- [ ] `python scripts/package_runtime.py` builds successfully
- [ ] Runtime validator passes against the extracted package
      (`python scripts/validate_skill.py --mode runtime --root <extracted>`)
- [ ] SHA-256 checksum file matches the built ZIP
- [ ] ZIP structure checked — exactly one root folder
      (`scholarly-corpus-builder/`) with `SKILL.md` directly inside it
- [ ] No development files included in the runtime ZIP (`evals/`, `tests/`,
      `scripts/`, `.github/`, `.git/`)
- [ ] No secrets included (`.env`, keys, credentials, tokens, local absolute
      paths)
- [ ] `git diff --check` passes (no whitespace errors)
- [ ] CI passes on the commit being tagged
- [ ] The intended tag (`vX.Y.Z`) does not already exist
- [ ] After the release workflow runs, both release artifacts are attached:
      `scholarly-corpus-builder-vX.Y.Z.zip` and its `.sha256` file

This checklist is for maintainers preparing a release and is not shipped to
Skill users.
