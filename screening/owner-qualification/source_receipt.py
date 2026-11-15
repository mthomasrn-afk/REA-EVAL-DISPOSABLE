#!/usr/bin/env python3
"""Bind an unmodified upstream REA v6.5.0 native cross-build to exact original bytes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PIN = "3b79af28e80785afce9f5998d8f03289402a1847"
BLOBS = {
    "native/windows/src/process.cc": "55e4153455b732115812d12d17c94709c1a65fdb",
    "native/windows/src/authority.hpp": "c8bed30dcbc6f151f3f8d2650d4958723f7290a0",
}


def build_receipt(root):
    root = Path(root).resolve()

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

    if git("rev-parse", "HEAD") != PIN:
        raise ValueError("PINNED_UPSTREAM_COMMIT_MISMATCH")
    if git("status", "--porcelain") != "":
        raise ValueError("UPSTREAM_SOURCE_DIRTY")
    for name, blob in BLOBS.items():
        if git("rev-parse", "HEAD:" + name) != blob:
            raise ValueError("ORIGINAL_OWNER_BLOB_MISMATCH:" + name)
    addon = root / "native/windows/build/rea-windows-x64.node"
    manifest = root / "native/windows/build/manifest.json"
    if not addon.is_file() or not manifest.is_file():
        raise ValueError("NATIVE_BUILD_MISSING")
    m = json.loads(manifest.read_text(encoding="utf-8"))
    sha = hashlib.sha256(addon.read_bytes()).hexdigest()
    if m.get("artifactSha256") != sha or m.get("packageVersion") != "6.5.0":
        raise ValueError("MANIFEST_INCONSISTENT_WITH_NATIVE_ARTIFACT")
    return {
        "schema": "rea.original-native-source-receipt.v1",
        "source_commit": PIN,
        "source_dirty": False,
        "verified_owner_blob_shas": BLOBS,
        "artifact_sha256": sha,
        "package_version": "6.5.0",
        "scope": "UNMODIFIED_UPSTREAM_CROSS_BUILD_NOT_QUALIFICATION",
        "original_c5": "NOT_QUALIFIED",
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: source_receipt.py UPSTREAM_ROOT RECEIPT_PATH")
    receipt = build_receipt(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("ORIGINAL_UPSTREAM_SOURCE_BOUND " + receipt["artifact_sha256"])
