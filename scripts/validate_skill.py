#!/usr/bin/env python3
"""Standard-library validator for the scholarly-corpus-builder skill repo.

Checks:
  - required files exist
  - SKILL.md has valid YAML-ish frontmatter with name/description
  - every JSONL eval file parses, and every record has a unique id
  - local markdown links ([text](path)) resolve to real files
  - fenced ```json blocks in references/ parse as valid JSON

No third-party dependencies.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "agents/openai.yaml",
    "references/corpus-policy.md",
    "references/source-hierarchy.md",
    "references/provenance-schema.md",
    "references/style-feature-schema.md",
    "references/journal-profile.md",
    "references/discipline-profile.md",
    "references/historical-profile.md",
    "references/author-profile.md",
    "references/copyright-boundary.md",
    "references/refresh-policy.md",
    "references/integration.md",
    "evals/source-selection.jsonl",
    "evals/corpus-selection.jsonl",
    "evals/copyright-boundary.jsonl",
    "evals/journal-profile.jsonl",
    "evals/author-profile.jsonl",
    "scripts/validate_skill.py",
]

MIN_TOTAL_EVALS = 40

errors = []
warnings = []


def check_required_files():
    for rel in REQUIRED_FILES:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            errors.append("missing required file: %s" % rel)


def check_frontmatter():
    path = os.path.join(ROOT, "SKILL.md")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        errors.append("SKILL.md: missing YAML frontmatter block")
        return
    fm = m.group(1)
    if "name:" not in fm:
        errors.append("SKILL.md frontmatter: missing 'name'")
    elif "scholarly-corpus-builder" not in fm:
        errors.append("SKILL.md frontmatter: name should be scholarly-corpus-builder")
    if "description:" not in fm:
        errors.append("SKILL.md frontmatter: missing 'description'")


def check_jsonl_files():
    total = 0
    for rel in os.listdir(os.path.join(ROOT, "evals")) if os.path.isdir(os.path.join(ROOT, "evals")) else []:
        if not rel.endswith(".jsonl"):
            continue
        path = os.path.join(ROOT, "evals", rel)
        seen_ids = set()
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append("evals/%s:%d: invalid JSON (%s)" % (rel, lineno, e))
                    continue
                total += 1
                rid = obj.get("id")
                if not rid:
                    errors.append("evals/%s:%d: missing 'id' field" % (rel, lineno))
                    continue
                if rid in seen_ids:
                    errors.append("evals/%s:%d: duplicate id '%s'" % (rel, lineno, rid))
                seen_ids.add(rid)
                for field in ("category", "task", "expected"):
                    if field not in obj:
                        errors.append("evals/%s:%d: record '%s' missing field '%s'" % (rel, lineno, rid, field))
    if total < MIN_TOTAL_EVALS:
        errors.append("total eval fixtures (%d) below minimum (%d)" % (total, MIN_TOTAL_EVALS))


LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def check_markdown_links():
    for dirpath, _dirnames, filenames in os.walk(ROOT):
        if os.sep + ".git" in dirpath:
            continue
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
                    rel_f = os.path.relpath(fpath, ROOT)
                    warnings.append("%s: local link target not found: %s" % (rel_f, target))


JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)


def check_json_blocks():
    refs_dir = os.path.join(ROOT, "references")
    if not os.path.isdir(refs_dir):
        return
    for fname in os.listdir(refs_dir):
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
                errors.append("references/%s: json block #%d does not parse (%s)" % (fname, i, e))


def main():
    check_required_files()
    check_frontmatter()
    check_jsonl_files()
    check_markdown_links()
    check_json_blocks()

    for w in warnings:
        print("WARNING: %s" % w)
    for e in errors:
        print("ERROR: %s" % e)

    print("\n%d error(s), %d warning(s)" % (len(errors), len(warnings)))
    if errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
