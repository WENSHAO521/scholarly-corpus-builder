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


def _canonicalize_to_lf(base_dir):
    """Rewrite every TEXT_SUFFIXES file under base_dir to use bare LF line
    endings, regardless of what the test process's own platform/newline
    translation wrote. Makes the fixture tree's starting point platform-
    independent before a test deliberately diverges it to CRLF."""
    for dirpath, _dirs, files in os.walk(base_dir):
        for fname in files:
            path = os.path.join(dirpath, fname)
            _, suffix = os.path.splitext(fname)
            if suffix.lower() not in package_runtime.TEXT_SUFFIXES:
                continue
            with open(path, "rb") as f:
                raw = f.read()
            normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            if normalized != raw:
                with open(path, "wb") as f:
                    f.write(normalized)


def _convert_to_crlf(src_dir, dest_dir):
    """Copy src_dir to dest_dir, rewriting every TEXT_SUFFIXES file's LF
    line endings to CRLF (simulating a Windows checkout with
    core.autocrlf=true converting the exact same git-tracked content)."""
    shutil.copytree(src_dir, dest_dir)
    for dirpath, _dirs, files in os.walk(dest_dir):
        for fname in files:
            path = os.path.join(dirpath, fname)
            _, suffix = os.path.splitext(fname)
            if suffix.lower() not in package_runtime.TEXT_SUFFIXES:
                continue
            with open(path, "rb") as f:
                raw = f.read()
            with open(path, "wb") as f:
                f.write(raw.replace(b"\n", b"\r\n"))


class TestLineEndingNormalization(TempTreeTestCase):
    """Regression coverage for the CRLF/LF packaging divergence fixed in
    v0.9.2: a Windows checkout (git core.autocrlf=true) and a Unix checkout
    of the exact same commit must produce byte-identical runtime ZIPs."""

    def test_crlf_and_lf_source_trees_produce_identical_zip_bytes(self):
        build_minimal_source_tree(self.source_root)
        _canonicalize_to_lf(self.source_root)

        crlf_root = tempfile.mkdtemp(prefix="scb-pkg-src-crlf-")
        crlf_root_child = os.path.join(crlf_root, "tree")
        try:
            _convert_to_crlf(self.source_root, crlf_root_child)

            lf_out = tempfile.mkdtemp(prefix="scb-pkg-out-lf-")
            crlf_out = tempfile.mkdtemp(prefix="scb-pkg-out-crlf-")
            try:
                _, _, digest_lf, _, _ = package_runtime.build(self.source_root, lf_out)
                _, _, digest_crlf, _, _ = package_runtime.build(crlf_root_child, crlf_out)
                self.assertEqual(
                    digest_lf,
                    digest_crlf,
                    msg="LF and CRLF checkouts of identical source content must "
                    "package to the same ZIP bytes",
                )
            finally:
                shutil.rmtree(lf_out, ignore_errors=True)
                shutil.rmtree(crlf_out, ignore_errors=True)
        finally:
            shutil.rmtree(crlf_root, ignore_errors=True)

    def test_packaged_text_files_are_lf_normalized(self):
        build_minimal_source_tree(self.source_root)
        _canonicalize_to_lf(self.source_root)
        crlf_root = tempfile.mkdtemp(prefix="scb-pkg-src-crlf2-")
        crlf_root_child = os.path.join(crlf_root, "tree")
        try:
            _convert_to_crlf(self.source_root, crlf_root_child)
            # Confirm the fixture actually has CRLF before packaging it --
            # otherwise this test would pass vacuously.
            with open(os.path.join(crlf_root_child, "README.md"), "rb") as f:
                self.assertIn(b"\r\n", f.read())

            zip_path, _, _, _, _ = package_runtime.build(crlf_root_child, self.out_dir)
            with zipfile.ZipFile(zip_path) as zf:
                for name in zf.namelist():
                    if name.endswith(".sha256"):
                        continue
                    _, suffix = os.path.splitext(name)
                    if suffix.lower() not in package_runtime.TEXT_SUFFIXES:
                        continue
                    data = zf.read(name)
                    self.assertNotIn(
                        b"\r\n", data, msg="packaged entry %r still contains CRLF" % name
                    )
                    self.assertNotIn(
                        b"\r", data, msg="packaged entry %r still contains a bare CR" % name
                    )
        finally:
            shutil.rmtree(crlf_root, ignore_errors=True)

    def test_canonical_runtime_bytes_normalizes_text_suffix(self):
        path = os.path.join(self.source_root, "sample.md")
        with open(path, "wb") as f:
            f.write(b"line one\r\nline two\rline three\n")
        result = package_runtime.canonical_runtime_bytes(path)
        self.assertEqual(result, b"line one\nline two\nline three\n")

    def test_canonical_runtime_bytes_preserves_binary_content(self):
        path = os.path.join(self.source_root, "sample.bin")
        binary_payload = b"\x00\r\n\xff\x01\r\x02\n\x89PNG\r\n\x1a\n"
        with open(path, "wb") as f:
            f.write(binary_payload)
        result = package_runtime.canonical_runtime_bytes(path)
        self.assertEqual(
            result,
            binary_payload,
            msg="a non-TEXT_SUFFIXES file must be packaged as raw, unmodified bytes",
        )

    def test_svg_asset_is_not_text_normalized(self):
        # architecture-diagram.svg is a real runtime file but is XML, not in
        # TEXT_SUFFIXES -- confirm the packager doesn't touch its bytes even
        # if it happens to contain CRLF.
        self.assertNotIn(".svg", package_runtime.TEXT_SUFFIXES)

    def test_extensionless_license_file_is_normalized(self):
        # Regression: LICENSE has no suffix, so TEXT_SUFFIXES-only matching
        # missed it -- a real windows-latest CI checkout of the exact same
        # commit packaged a different LICENSE byte sequence than
        # ubuntu-latest until TEXT_FILENAMES was added.
        path = os.path.join(self.source_root, "LICENSE")
        with open(path, "wb") as f:
            f.write(b"MIT License\r\n\r\nCopyright (c) 2026\r\n")
        result = package_runtime.canonical_runtime_bytes(path)
        self.assertNotIn(b"\r", result)
        self.assertEqual(result, b"MIT License\n\nCopyright (c) 2026\n")

    def test_extensionless_version_file_is_normalized(self):
        path = os.path.join(self.source_root, "VERSION")
        with open(path, "wb") as f:
            f.write(b"0.9.2\r\n")
        result = package_runtime.canonical_runtime_bytes(path)
        self.assertEqual(result, b"0.9.2\n")

    def test_unknown_extensionless_file_is_not_text_normalized(self):
        # Only the specific known runtime text filenames in TEXT_FILENAMES
        # are matched by basename -- an arbitrary extensionless file (e.g.
        # a binary fixture with no suffix) must not be swept in.
        path = os.path.join(self.source_root, "some_binary_blob")
        binary_payload = b"\x00\r\n\xff\x01\r\x02\n"
        with open(path, "wb") as f:
            f.write(binary_payload)
        result = package_runtime.canonical_runtime_bytes(path)
        self.assertEqual(result, binary_payload)


class TestCrossPlatformZipMetadata(TempTreeTestCase):
    def test_all_entries_use_stored_not_deflated_compression(self):
        build_minimal_source_tree(self.source_root)
        zip_path, _, _, _, _ = package_runtime.build(self.source_root, self.out_dir)
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                self.assertEqual(
                    info.compress_type,
                    zipfile.ZIP_STORED,
                    msg="%r uses compress_type %r, expected ZIP_STORED for "
                    "byte-deterministic packaging independent of zlib version"
                    % (info.filename, info.compress_type),
                )

    def test_all_entries_pin_create_system_to_unix(self):
        build_minimal_source_tree(self.source_root)
        zip_path, _, _, _, _ = package_runtime.build(self.source_root, self.out_dir)
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                self.assertEqual(
                    info.create_system,
                    3,
                    msg="%r has create_system %r, expected 3 (Unix) so Windows "
                    "and Linux builds produce identical entry metadata"
                    % (info.filename, info.create_system),
                )

    def test_all_entries_use_fixed_timestamp(self):
        build_minimal_source_tree(self.source_root)
        zip_path, _, _, _, _ = package_runtime.build(self.source_root, self.out_dir)
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                self.assertEqual(info.date_time, package_runtime.FIXED_ZIP_DATE_TIME)

    def test_entries_are_in_deterministic_sorted_order(self):
        build_minimal_source_tree(self.source_root)
        zip_path, _, _, _, _ = package_runtime.build(self.source_root, self.out_dir)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        # manifest is always appended last by write_deterministic_zip; every
        # other entry must be in sorted order.
        body = [n for n in names if not n.endswith("release-manifest.json")]
        self.assertEqual(body, sorted(body))


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
