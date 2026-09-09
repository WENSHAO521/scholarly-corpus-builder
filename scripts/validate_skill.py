#!/usr/bin/env python3
"""Validator for the scholarly-corpus-builder skill repository.

Supports two modes that share the same underlying checks:

  python scripts/validate_skill.py
  python scripts/validate_skill.py --mode source
      Validates the full development repository (docs, references, evals,
      scripts, tests, CI workflows).

  python scripts/validate_skill.py --mode runtime --root <directory>
      Validates a runtime package tree (what an Agent Skill host actually
      needs to load) — no evals/, scripts/, tests/, .github/, or .git/.

No third-party dependencies (Python standard library only).
"""

import argparse
import ast
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

# Reference files that SKILL.md can load at runtime. This is the single
# source of truth for what references/ must contain in BOTH modes: source
# mode checks that every file on disk is accounted for here (drift check),
# and package_runtime.py copies exactly these files into the runtime
# package.
RUNTIME_REFERENCE_FILES = [
    "author-profile.md",
    "copyright-boundary.md",
    "corpus-policy.md",
    "discipline-profile.md",
    "historical-profile.md",
    "integration.md",
    "journal-profile.md",
    "oa-resolution.md",
    "provenance-schema.md",
    "refresh-policy.md",
    "source-adapters.md",
    "source-hierarchy.md",
    "stability-analysis.md",
    "style-feature-schema.md",
]

# The scb/ Python package is a controlled, version-controlled source
# directory (no dev artifacts mixed in — tests live under tests/, not
# here), so — like references/ above — its contents are safely derived
# from a directory scan rather than hand-maintained as a ~45-entry
# static list. See discover_scb_modules().
SCB_PACKAGE_DIR = "scb"

# Anchoring files that must exist to confirm the scb/ package (and its
# subpackages) are actually present, without hand-listing every module.
SCB_ANCHOR_FILES = [
    "scb/__init__.py",
    "scb/adapters/__init__.py",
    "scb/analytics/__init__.py",
    "scb/profiles/__init__.py",
]


def discover_scb_modules(root):
    scb_dir = os.path.join(root, SCB_PACKAGE_DIR)
    if not os.path.isdir(scb_dir):
        return []
    modules = []
    for dirpath, dirnames, filenames in os.walk(scb_dir):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fname in filenames:
            if fname.endswith(".py"):
                rel = os.path.relpath(os.path.join(dirpath, fname), root)
                modules.append(rel.replace(os.sep, "/"))
    return sorted(modules)


# Files required for the Skill to actually be usable at runtime.
RUNTIME_REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "LICENSE",
    "VERSION",
    "agents/openai.yaml",
    "ARCHITECTURE.html",
] + ["references/%s" % name for name in RUNTIME_REFERENCE_FILES] + SCB_ANCHOR_FILES

# Additional files required only in the full development repository.
SOURCE_ONLY_REQUIRED_FILES = [
    "CHANGELOG.md",
    "RELEASE_CHECKLIST.md",
    ".gitignore",
    "scripts/validate_skill.py",
    "scripts/package_runtime.py",
    "tests/test_validate_skill.py",
    "tests/test_package_runtime.py",
    ".github/workflows/validate.yml",
    ".github/workflows/release.yml",
    ".github/workflows/live-check.yml",
]

SOURCE_REQUIRED_EVAL_FILES = [
    "evals/source-selection.jsonl",
    "evals/corpus-selection.jsonl",
    "evals/copyright-boundary.jsonl",
    "evals/journal-profile.jsonl",
    "evals/author-profile.jsonl",
    "evals/oa-resolution.jsonl",
    "evals/dedup-versioning.jsonl",
    "evals/analytics-honesty.jsonl",
    "evals/compiler-protocol.jsonl",
    "evals/refresh-and-robustness.jsonl",
    "evals/multilingual-and-tooling.jsonl",
    "evals/production-hardening.jsonl",
]

MIN_TOTAL_EVALS = 140

# Directories/files that must NOT appear anywhere in a runtime package.
FORBIDDEN_RUNTIME_DIR_NAMES = {
    "tests", "evals", "scripts", ".github", ".git", "dist", "__pycache__",
    ".pytest_cache", ".idea", ".vscode",
}
FORBIDDEN_RUNTIME_FILE_PATTERNS = [
    re.compile(r"\.pyc$"),
    re.compile(r"^\.DS_Store$"),
    re.compile(r"^\.env(\..*)?$"),
    re.compile(r"\.key$"),
    re.compile(r"\.pem$"),
    re.compile(r"^credentials.*", re.IGNORECASE),
    re.compile(r"^secrets.*", re.IGNORECASE),
]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    @property
    def ok(self):
        return not self.errors


def check_required_files(root, report, file_list):
    for rel in file_list:
        path = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            report.error("missing required file: %s" % rel)


def check_frontmatter(root, report):
    path = os.path.join(root, "SKILL.md")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        report.error("SKILL.md: missing YAML frontmatter block")
        return
    fm = m.group(1)
    if "name:" not in fm:
        report.error("SKILL.md frontmatter: missing 'name'")
    elif "scholarly-corpus-builder" not in fm:
        report.error("SKILL.md frontmatter: name should be scholarly-corpus-builder")
    if "description:" not in fm:
        report.error("SKILL.md frontmatter: missing 'description'")


def check_jsonl_files(root, report):
    evals_dir = os.path.join(root, "evals")
    if not os.path.isdir(evals_dir):
        report.error("missing evals/ directory")
        return
    total = 0
    all_ids = set()
    for rel in sorted(os.listdir(evals_dir)):
        if not rel.endswith(".jsonl"):
            continue
        path = os.path.join(evals_dir, rel)
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    report.error("evals/%s:%d: invalid JSON (%s)" % (rel, lineno, e))
                    continue
                total += 1
                rid = obj.get("id")
                if not rid:
                    report.error("evals/%s:%d: missing 'id' field" % (rel, lineno))
                    continue
                if rid in all_ids:
                    report.error("evals/%s:%d: duplicate id '%s'" % (rel, lineno, rid))
                all_ids.add(rid)
                for field in ("category", "task", "expected"):
                    if field not in obj:
                        report.error(
                            "evals/%s:%d: record '%s' missing field '%s'" % (rel, lineno, rid, field)
                        )
    if total < MIN_TOTAL_EVALS:
        report.error("total eval fixtures (%d) below minimum (%d)" % (total, MIN_TOTAL_EVALS))


def check_markdown_links(root, report):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fname in filenames:
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()
            for match in LINK_RE.finditer(text):
                target = match.group(1).strip()
                if re.match(r"^[a-zA-Z]+://", target):
                    continue
                if target.startswith("#") or target.startswith("mailto:"):
                    continue
                target = target.split("#", 1)[0]
                if not target:
                    continue
                resolved = os.path.normpath(os.path.join(dirpath, target))
                if not os.path.exists(resolved):
                    rel_f = os.path.relpath(fpath, root)
                    report.error("%s: local link target not found: %s" % (rel_f, target))


def check_json_blocks(root, report):
    refs_dir = os.path.join(root, "references")
    if not os.path.isdir(refs_dir):
        return
    for fname in sorted(os.listdir(refs_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(refs_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            text = f.read()
        for i, match in enumerate(JSON_BLOCK_RE.finditer(text), start=1):
            block = match.group(1).strip()
            if not block:
                continue
            try:
                json.loads(block)
            except json.JSONDecodeError as e:
                report.error("references/%s: json block #%d does not parse (%s)" % (fname, i, e))


def check_references_allowlist_drift(root, report):
    """Source-mode only: every file physically in references/ must be on the
    runtime allowlist, and every allowlisted file must exist on disk."""
    refs_dir = os.path.join(root, "references")
    if not os.path.isdir(refs_dir):
        return
    on_disk = {f for f in os.listdir(refs_dir) if f.endswith(".md")}
    allowlisted = set(RUNTIME_REFERENCE_FILES)
    for extra in sorted(on_disk - allowlisted):
        report.error(
            "references/%s exists on disk but is not in RUNTIME_REFERENCE_FILES "
            "(update scripts/validate_skill.py's allowlist)" % extra
        )
    for missing in sorted(allowlisted - on_disk):
        report.error(
            "RUNTIME_REFERENCE_FILES lists references/%s but the file does not exist" % missing
        )


def check_scb_package(root, report):
    """Confirms scb/ and its subpackages are present, and that every
    discovered module at least parses (ast.parse — a syntax check only;
    it never imports/executes the module, so this stays side-effect-free
    and fast in both source and runtime validation)."""
    modules = discover_scb_modules(root)
    if not modules:
        report.error("scb/ package not found or contains no .py modules")
        return
    for rel in modules:
        path = os.path.join(root, rel.replace("/", os.sep))
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
        try:
            ast.parse(source, filename=rel)
        except SyntaxError as e:
            report.error("scb module %s does not parse: %s" % (rel, e))


def check_version_file(root, report):
    path = os.path.join(root, "VERSION")
    if not os.path.isfile(path):
        report.error("missing required file: VERSION")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not re.match(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$", content):
        report.error("VERSION file content is not a valid semantic version: %r" % content)
    if content.startswith("v"):
        report.error("VERSION must not include a leading 'v' (found %r)" % content)


def check_forbidden_runtime_entries(root, report):
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        for d in list(dirnames):
            if d in FORBIDDEN_RUNTIME_DIR_NAMES:
                rel = d if rel_dir == "." else os.path.join(rel_dir, d)
                report.error("forbidden development directory present in runtime tree: %s/" % rel)
        for fname in filenames:
            for pattern in FORBIDDEN_RUNTIME_FILE_PATTERNS:
                if pattern.search(fname):
                    rel = fname if rel_dir == "." else os.path.join(rel_dir, fname)
                    report.error("forbidden file present in runtime tree: %s" % rel)
                    break


def run_source_validation(root):
    report = Report()
    check_required_files(root, report, RUNTIME_REQUIRED_FILES)
    check_required_files(root, report, SOURCE_ONLY_REQUIRED_FILES)
    check_required_files(root, report, SOURCE_REQUIRED_EVAL_FILES)
    check_version_file(root, report)
    check_frontmatter(root, report)
    check_jsonl_files(root, report)
    check_markdown_links(root, report)
    check_json_blocks(root, report)
    check_references_allowlist_drift(root, report)
    check_scb_package(root, report)
    return report


def run_runtime_validation(root):
    report = Report()
    check_required_files(root, report, RUNTIME_REQUIRED_FILES)
    check_version_file(root, report)
    check_frontmatter(root, report)
    check_markdown_links(root, report)
    check_json_blocks(root, report)
    check_forbidden_runtime_entries(root, report)
    check_scb_package(root, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=["source", "runtime"], default="source",
        help="'source' validates the development repository (default); "
             "'runtime' validates a packaged/extracted runtime tree.",
    )
    parser.add_argument(
        "--root", default=None,
        help="Root directory to validate. Defaults to the repository root "
             "for source mode. Required for runtime mode.",
    )
    args = parser.parse_args(argv)

    if args.mode == "source":
        root = args.root or REPO_ROOT
        report = run_source_validation(root)
    else:
        if not args.root:
            print("ERROR: --root is required with --mode runtime")
            sys.exit(2)
        root = args.root
        report = run_runtime_validation(root)

    for w in report.warnings:
        print("WARNING: %s" % w)
    for e in report.errors:
        print("ERROR: %s" % e)

    print("\n[%s mode] %d error(s), %d warning(s)" % (args.mode, len(report.errors), len(report.warnings)))
    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
