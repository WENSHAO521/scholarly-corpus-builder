"""Unit tests for scripts/package_runtime.py.

Packaging tests build a fake source tree in a temporary directory and pass
it via package_runtime.build(source_root=..., out_dir=...) so the real
repository is never mutated. A handful of integration-style tests also
package the real repository into a temporary out-dir to confirm the actual
release artifact is well-formed.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")

sys.path.insert(0, TESTS_DIR)
from test_validate_skill import (  # noqa: E402
    build_minimal_source_tree,
    validate_skill,
)


def _load_module(name, filename):
    path = os.path.join(SCRIPTS_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package_runtime = _load_module("package_runtime", "package_runtime.py")


class TempTreeTestCase(unittest.TestCase):
    def setUp(self):
        self.source_root = tempfile.mkdtemp(prefix="scb-pkg-src-")
        self.out_dir = tempfile.mkdtemp(prefix="scb-pkg-out-")

    def tearDown(self):
        shutil.rmtree(self.source_root, ignore_errors=True)
        shutil.rmtree(self.out_dir, ignore_errors=True)


class TestPackagingFakeSource(TempTreeTestCase):
    def test_package_builds_successfully(self):
        build_minimal_source_tree(self.source_root)
        zip_path, checksum_path, digest, manifest, report = package_runtime.build(
            self.source_root, self.out_dir
        )
        self.assertTrue(os.path.isfile(zip_path))
        self.assertTrue(os.path.isfile(checksum_path))
        self.assertTrue(report.ok)

    def test_filename_matches_version(self):
        build_minimal_source_tree(self.source_root)
        zip_path, _, _, _, _ = package_runtime.build(self.source_root, self.out_dir)
        self.assertEqual(os.path.basename(zip_path), "scholarly-corpus-builder-v0.1.1.zip")

    def test_single_root_folder_and_skill_md_placement(self):
        build_minimal_source_tree(self.source_root)
        zip_path, _, _, _, _ = package_runtime.build(self.source_root, self.out_dir)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        roots = {n.split("/", 1)[0] for n in names}
        self.assertEqual(roots, {"scholarly-corpus-builder"})
        self.assertIn("scholarly-corpus-builder/SKILL.md", names)

    def test_all_runtime_references_present(self):
        build_minimal_source_tree(self.source_root)
        zip_path, _, _, _, _ = package_runtime.build(self.source_root, self.out_dir)
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
        for ref in validate_skill.RUNTIME_REFERENCE_FILES:
            self.assertIn("scholarly-corpus-builder/references/%s" % ref, names)

    def test_development_directories_absent(self):
        build_minimal_source_tree(self.source_root)
        zip_path, _, _, _, _ = package_runtime.build(self.source_root, self.out_dir)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        for forbidden in ("evals/", "tests/", "scripts/", ".github/"):
            self.assertFalse(
                any(forbidden in n for n in names),
                msg="forbidden path fragment %r found in package: %r" % (forbidden, names),
            )

    def test_manifest_version_correct(self):
        build_minimal_source_tree(self.source_root)
        _, _, _, manifest, _ = package_runtime.build(self.source_root, self.out_dir)
        self.assertEqual(manifest["version"], "0.1.1")
        self.assertEqual(manifest["name"], "scholarly-corpus-builder")
        self.assertEqual(manifest["entrypoint"], "SKILL.md")

    def test_sha256_matches_checksum_file(self):
        build_minimal_source_tree(self.source_root)
        zip_path, checksum_path, digest, _, _ = package_runtime.build(self.source_root, self.out_dir)
        actual = package_runtime.sha256_of_file(zip_path)
        self.assertEqual(actual, digest)
        with open(checksum_path, "r", encoding="utf-8") as f:
            line = f.read().strip()
        self.assertTrue(line.startswith(digest))
        self.assertIn(os.path.basename(zip_path), line)

    def test_extracted_runtime_passes_runtime_validator(self):
        build_minimal_source_tree(self.source_root)
        zip_path, _, _, _, _ = package_runtime.build(self.source_root, self.out_dir)
        with tempfile.TemporaryDirectory(prefix="scb-extract-") as extract_dir:
            extracted_root = package_runtime.extract_zip_single_root(zip_path, extract_dir)
            report = validate_skill.run_runtime_validation(extracted_root)
            self.assertTrue(report.ok, msg="; ".join(report.errors))

    def test_reproducible_build_same_bytes(self):
        build_minimal_source_tree(self.source_root)
        out_dir_2 = tempfile.mkdtemp(prefix="scb-pkg-out2-")
        try:
            zip_path_1, _, digest_1, _, _ = package_runtime.build(self.source_root, self.out_dir)
            zip_path_2, _, digest_2, _, _ = package_runtime.build(self.source_root, out_dir_2)
            self.assertEqual(digest_1, digest_2)
            with open(zip_path_1, "rb") as f1, open(zip_path_2, "rb") as f2:
                self.assertEqual(f1.read(), f2.read())
        finally:
            shutil.rmtree(out_dir_2, ignore_errors=True)

    def test_missing_required_runtime_source_fails(self):
        build_minimal_source_tree(self.source_root)
        os.remove(os.path.join(self.source_root, "references", validate_skill.RUNTIME_REFERENCE_FILES[0]))
        with self.assertRaises(package_runtime.PackagingError):
            package_runtime.build(self.source_root, self.out_dir)

    def test_invalid_version_fails(self):
        build_minimal_source_tree(self.source_root)
        with open(os.path.join(self.source_root, "VERSION"), "w", encoding="utf-8") as f:
            f.write("v0.1.1")
        with self.assertRaises(package_runtime.PackagingError):
            package_runtime.build(self.source_root, self.out_dir)


class TestPackagingRealRepository(unittest.TestCase):
    """Integration check against the actual repository."""

    def setUp(self):
        self.out_dir = tempfile.mkdtemp(prefix="scb-pkg-real-out-")

    def tearDown(self):
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def test_real_repo_packages_and_self_validates(self):
        zip_path, checksum_path, digest, manifest, report = package_runtime.build(
            REPO_ROOT, self.out_dir
        )
        self.assertTrue(os.path.isfile(zip_path))
        self.assertTrue(os.path.isfile(checksum_path))
        self.assertTrue(report.ok, msg="; ".join(report.errors))
        with open(os.path.join(REPO_ROOT, "VERSION"), "r", encoding="utf-8") as f:
            version = f.read().strip()
        self.assertEqual(manifest["version"], version)
        self.assertEqual(os.path.basename(zip_path), "scholarly-corpus-builder-v%s.zip" % version)


if __name__ == "__main__":
    unittest.main()
