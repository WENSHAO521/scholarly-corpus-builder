#!/usr/bin/env python3
"""Build a deterministic runtime package for the scholarly-corpus-builder skill.

Copies an explicit allowlist of files (never "copy everything then delete")
into scholarly-corpus-builder/ inside a zip archive, writes a release
manifest and a SHA-256 checksum, then self-validates the built package by
extracting it to a temporary directory and running the runtime validator
against it.

Usage:
    python scripts/package_runtime.py [--out-dir dist] [--source-root .]

Python standard library only.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
PACKAGE_NAME = "scholarly-corpus-builder"

sys.path.insert(0, SCRIPT_DIR)
import validate_skill  # noqa: E402  (local module, path set above)

# Fixed timestamp so identical source content produces identical archive
# bytes regardless of when/where the build runs. (2026-01-01 00:00:00, a
# valid DOS/ZIP timestamp.)
FIXED_ZIP_DATE_TIME = (2026, 1, 1, 0, 0, 0)

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")


class PackagingError(Exception):
    pass


def read_version(source_root):
    version_path = os.path.join(source_root, "VERSION")
    if not os.path.isfile(version_path):
        raise PackagingError("missing VERSION file at %s" % version_path)
    with open(version_path, "r", encoding="utf-8") as f:
        version = f.read().strip()
    if not version or version.startswith("v") or not VERSION_RE.match(version):
        raise PackagingError("invalid VERSION content: %r" % version)
    return version


def runtime_file_list():
    """Explicit allowlist of repo-relative paths to include in the package.

    This never copies the whole repository and deletes things afterward —
    every entry here is a deliberate inclusion, sourced from the same
    allowlist the runtime validator checks against.
    """
    return sorted(validate_skill.RUNTIME_REQUIRED_FILES)


def build_manifest(file_arcnames, version):
    return {
        "name": PACKAGE_NAME,
        "version": version,
        "release_type": "runtime",
        "entrypoint": "SKILL.md",
        "built_from": "source repository",
        "files": sorted(file_arcnames),
    }


def write_deterministic_zip(source_root, zip_path, entries, manifest_bytes):
    """entries: list of (repo_relative_src_path, arcname_within_package)."""
    tmp_path = zip_path + ".tmp"
    with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src_rel, arcname in sorted(entries, key=lambda pair: pair[1]):
            src_path = os.path.join(source_root, src_rel.replace("/", os.sep))
            with open(src_path, "rb") as f:
                data = f.read()
            arcpath = "%s/%s" % (PACKAGE_NAME, arcname)
            _write_deterministic_entry(zf, arcpath, data)
        manifest_arcpath = "%s/release-manifest.json" % PACKAGE_NAME
        _write_deterministic_entry(zf, manifest_arcpath, manifest_bytes)
    os.replace(tmp_path, zip_path)


def _write_deterministic_entry(zf, arcname, data):
    info = zipfile.ZipInfo(filename=arcname, date_time=FIXED_ZIP_DATE_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zf.writestr(info, data)


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_zip_single_root(zip_path, dest_dir):
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        roots = {name.split("/", 1)[0] for name in names if name}
        if len(roots) != 1:
            raise AssertionError("zip does not have exactly one root directory: %r" % roots)
        root_name = next(iter(roots))
        if root_name != PACKAGE_NAME:
            raise AssertionError(
                "zip root directory is %r, expected %r" % (root_name, PACKAGE_NAME)
            )
        zf.extractall(dest_dir)
    return os.path.join(dest_dir, root_name)


def self_validate(zip_path, expected_version):
    with tempfile.TemporaryDirectory(prefix="scb-runtime-check-") as tmp:
        extracted_root = extract_zip_single_root(zip_path, tmp)

        skill_md = os.path.join(extracted_root, "SKILL.md")
        if not os.path.isfile(skill_md):
            raise AssertionError("SKILL.md missing directly under package root")

        manifest_path = os.path.join(extracted_root, "release-manifest.json")
        if not os.path.isfile(manifest_path):
            raise AssertionError("release-manifest.json missing from package")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if manifest.get("version") != expected_version:
            raise AssertionError(
                "manifest version %r does not match VERSION %r"
                % (manifest.get("version"), expected_version)
            )
        manifest_text = json.dumps(manifest)
        if "\\" in manifest_text:
            raise AssertionError("manifest contains a Windows-style absolute path")
        if REPO_ROOT.replace("\\", "/") in manifest_text or os.path.expanduser("~") in manifest_text:
            raise AssertionError("manifest leaks a local filesystem path")

        report = validate_skill.run_runtime_validation(extracted_root)
        if not report.ok:
            details = "; ".join(report.errors)
            raise AssertionError("runtime validation failed on packaged output: %s" % details)

        return report


def build(source_root, out_dir):
    """Build the runtime package from source_root into out_dir.

    Returns (zip_path, checksum_path, digest, manifest, self_validation_report).
    Raises PackagingError or AssertionError on any failure — never produces
    a partially-valid package silently.
    """
    version = read_version(source_root)
    os.makedirs(out_dir, exist_ok=True)

    arcnames = []
    entries = []
    for rel in runtime_file_list():
        src_path = os.path.join(source_root, rel.replace("/", os.sep))
        if not os.path.isfile(src_path):
            raise PackagingError("required runtime source file missing: %s" % rel)
        arcnames.append(rel)
        entries.append((rel, rel))

    manifest = build_manifest(arcnames + ["release-manifest.json"], version)
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=False) + "\n").encode("utf-8")

    zip_name = "%s-v%s.zip" % (PACKAGE_NAME, version)
    zip_path = os.path.join(out_dir, zip_name)
    write_deterministic_zip(source_root, zip_path, entries, manifest_bytes)

    digest = sha256_of_file(zip_path)
    checksum_path = zip_path + ".sha256"
    with open(checksum_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("%s  %s\n" % (digest, zip_name))

    report = self_validate(zip_path, version)
    return zip_path, checksum_path, digest, manifest, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=os.path.join(REPO_ROOT, "dist"))
    parser.add_argument("--source-root", default=REPO_ROOT)
    args = parser.parse_args(argv)

    try:
        zip_path, checksum_path, digest, manifest, report = build(args.source_root, args.out_dir)
    except (PackagingError, AssertionError) as e:
        print("ERROR: %s" % e)
        sys.exit(1)

    print("Built: %s" % zip_path)
    print("SHA256: %s" % digest)
    print("Checksum file: %s" % checksum_path)
    print("Runtime self-validation: %d error(s), %d warning(s)" % (len(report.errors), len(report.warnings)))
    for w in report.warnings:
        print("WARNING: %s" % w)
    sys.exit(0)


if __name__ == "__main__":
    main()
