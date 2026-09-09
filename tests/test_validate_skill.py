"""Unit tests for scripts/validate_skill.py.

All tests build fixture trees inside temporary directories. None of these
tests mutate the real repository.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")


def _load_module(name, filename):
    path = os.path.join(SCRIPTS_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_skill = _load_module("validate_skill", "validate_skill.py")


VALID_FRONTMATTER = (
    "---\n"
    "name: scholarly-corpus-builder\n"
    "description: Build provenance-aware scholarly corpora and writing profiles.\n"
    "---\n\n"
    "# Scholarly Corpus Builder\n\nBody text.\n"
)


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _make_eval_fixtures(total_needed):
    """Distribute >= total_needed fixtures across the 5 required eval files."""
    filenames = [os.path.basename(p) for p in validate_skill.SOURCE_REQUIRED_EVAL_FILES]
    per_file = (total_needed // len(filenames)) + 1
    fixtures_by_file = {}
    counter = 0
    for fname in filenames:
        lines = []
        for _ in range(per_file):
            counter += 1
            rec = {
                "id": "fx-%03d" % counter,
                "category": "test_category",
                "task": "synthetic fixture task %d" % counter,
                "expected": "synthetic_expected_outcome",
            }
            lines.append(json.dumps(rec))
        fixtures_by_file[fname] = "\n".join(lines) + "\n"
    return fixtures_by_file


def build_minimal_source_tree(base_dir):
    """Build a minimal, fully valid development repository tree."""
    _write(os.path.join(base_dir, "SKILL.md"), VALID_FRONTMATTER)
    _write(os.path.join(base_dir, "README.md"), "# README\n\nSee [SKILL](SKILL.md).\n")
    _write(os.path.join(base_dir, "LICENSE"), "MIT License\n")
    _write(os.path.join(base_dir, "VERSION"), "0.1.1")
    _write(os.path.join(base_dir, "CHANGELOG.md"), "# Changelog\n")
    _write(os.path.join(base_dir, "agents", "openai.yaml"), "name: scholarly-corpus-builder\n")

    for ref in validate_skill.RUNTIME_REFERENCE_FILES:
        content = "# %s\n\nExample:\n\n```json\n{\"a\": 1}\n```\n" % ref
        _write(os.path.join(base_dir, "references", ref), content)

    for rel in validate_skill.SCB_ANCHOR_FILES:
        _write(os.path.join(base_dir, rel.replace("/", os.sep)), '"""stub module"""\n')

    fixtures_by_file = _make_eval_fixtures(validate_skill.MIN_TOTAL_EVALS)
    for fname, content in fixtures_by_file.items():
        _write(os.path.join(base_dir, "evals", fname), content)

    _write(os.path.join(base_dir, "scripts", "validate_skill.py"), "# stub\n")
    _write(os.path.join(base_dir, "scripts", "package_runtime.py"), "# stub\n")
    for rel in validate_skill.SOURCE_ONLY_REQUIRED_FILES:
        target = os.path.join(base_dir, rel.replace("/", os.sep))
        if not os.path.isfile(target):
            _write(target, "# stub\n")


def build_minimal_runtime_tree(base_dir):
    """Build a minimal, fully valid runtime package tree (no dev files)."""
    _write(os.path.join(base_dir, "SKILL.md"), VALID_FRONTMATTER)
    _write(os.path.join(base_dir, "README.md"), "# README\n")
    _write(os.path.join(base_dir, "LICENSE"), "MIT License\n")
    _write(os.path.join(base_dir, "VERSION"), "0.1.1")
    _write(os.path.join(base_dir, "agents", "openai.yaml"), "name: scholarly-corpus-builder\n")
    for ref in validate_skill.RUNTIME_REFERENCE_FILES:
        _write(os.path.join(base_dir, "references", ref), "# %s\n" % ref)
    for rel in validate_skill.SCB_ANCHOR_FILES:
        _write(os.path.join(base_dir, rel.replace("/", os.sep)), '"""stub module"""\n')


class TempTreeTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="scb-validate-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestSourceValidation(TempTreeTestCase):
    def test_valid_source_tree_passes(self):
        build_minimal_source_tree(self.tmp)
        report = validate_skill.run_source_validation(self.tmp)
        self.assertEqual(report.errors, [], msg="; ".join(report.errors))
        self.assertTrue(report.ok)

    def test_missing_skill_md_fails(self):
        build_minimal_source_tree(self.tmp)
        os.remove(os.path.join(self.tmp, "SKILL.md"))
        report = validate_skill.run_source_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("SKILL.md" in e for e in report.errors))

    def test_invalid_frontmatter_fails(self):
        build_minimal_source_tree(self.tmp)
        _write(os.path.join(self.tmp, "SKILL.md"), "# No frontmatter here\n")
        report = validate_skill.run_source_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("frontmatter" in e for e in report.errors))

    def test_broken_markdown_link_fails(self):
        build_minimal_source_tree(self.tmp)
        _write(
            os.path.join(self.tmp, "README.md"),
            "# README\n\nSee [missing](references/does-not-exist.md).\n",
        )
        report = validate_skill.run_source_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("link target not found" in e for e in report.errors))

    def test_invalid_jsonl_fails(self):
        build_minimal_source_tree(self.tmp)
        path = os.path.join(self.tmp, "evals", "author-profile.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write("{not valid json\n")
        report = validate_skill.run_source_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("invalid JSON" in e for e in report.errors))

    def test_duplicate_fixture_id_fails(self):
        build_minimal_source_tree(self.tmp)
        path = os.path.join(self.tmp, "evals", "author-profile.jsonl")
        with open(path, "r", encoding="utf-8") as f:
            first_line = f.readline()
        with open(path, "a", encoding="utf-8") as f:
            f.write(first_line if first_line.endswith("\n") else first_line + "\n")
        report = validate_skill.run_source_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("duplicate id" in e for e in report.errors))

    def test_missing_required_source_file_fails(self):
        build_minimal_source_tree(self.tmp)
        os.remove(os.path.join(self.tmp, "CHANGELOG.md"))
        report = validate_skill.run_source_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("CHANGELOG.md" in e for e in report.errors))

    def test_invalid_version_fails(self):
        build_minimal_source_tree(self.tmp)
        _write(os.path.join(self.tmp, "VERSION"), "v0.1.1")
        report = validate_skill.run_source_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("VERSION" in e for e in report.errors))

    def test_reference_allowlist_drift_extra_file_fails(self):
        build_minimal_source_tree(self.tmp)
        _write(os.path.join(self.tmp, "references", "unlisted-file.md"), "# Unlisted\n")
        report = validate_skill.run_source_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("not in RUNTIME_REFERENCE_FILES" in e for e in report.errors))


class TestRuntimeValidation(TempTreeTestCase):
    def test_valid_runtime_tree_passes(self):
        build_minimal_runtime_tree(self.tmp)
        report = validate_skill.run_runtime_validation(self.tmp)
        self.assertEqual(report.errors, [], msg="; ".join(report.errors))
        self.assertTrue(report.ok)

    def test_runtime_missing_reference_file_fails(self):
        build_minimal_runtime_tree(self.tmp)
        os.remove(os.path.join(self.tmp, "references", validate_skill.RUNTIME_REFERENCE_FILES[0]))
        report = validate_skill.run_runtime_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("missing required file" in e for e in report.errors))

    def test_runtime_tree_with_dev_directory_fails(self):
        build_minimal_runtime_tree(self.tmp)
        _write(os.path.join(self.tmp, "tests", "test_something.py"), "# stub\n")
        report = validate_skill.run_runtime_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("forbidden development directory" in e for e in report.errors))

    def test_runtime_tree_with_secret_file_fails(self):
        build_minimal_runtime_tree(self.tmp)
        _write(os.path.join(self.tmp, ".env"), "SECRET=1\n")
        report = validate_skill.run_runtime_validation(self.tmp)
        self.assertFalse(report.ok)
        self.assertTrue(any("forbidden file" in e for e in report.errors))


class TestRealRepository(unittest.TestCase):
    """Sanity check that the actual repository (not a fixture) still passes."""

    def test_real_repo_source_mode_passes(self):
        report = validate_skill.run_source_validation(REPO_ROOT)
        self.assertEqual(report.errors, [], msg="; ".join(report.errors))


if __name__ == "__main__":
    unittest.main()
