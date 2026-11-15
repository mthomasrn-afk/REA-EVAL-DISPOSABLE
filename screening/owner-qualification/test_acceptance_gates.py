"""Deterministic no-network negative gates for the original owner acceptance package."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from owner_host_acceptance import PIN, ORIGINAL, preflight


class OriginalOwnerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        d = Path(self.temp.name)
        self.addon = d / "rea-windows-x64.node"
        self.manifest = d / "manifest.json"
        self.receipt = d / "source_receipt.json"
        self.addon.write_bytes(b"synthetic-not-a-real-binary")
        sha = hashlib.sha256(self.addon.read_bytes()).hexdigest()
        self.m = {"packageVersion": "6.5.0", "platform": "win32",
                  "architecture": "x64", "artifactSha256": sha}
        self.r = {"source_commit": PIN, "source_dirty": False,
                  "artifact_sha256": sha}
        self.flush()

    def flush(self):
        self.manifest.write_text(json.dumps(self.m), encoding="utf-8")
        self.receipt.write_text(json.dumps(self.r), encoding="utf-8")

    def accepted(self):
        return preflight(self.addon, self.manifest, self.receipt)

    def test_positive_synthetic_receipt_does_not_qualify_component(self):
        proof = self.accepted()
        self.assertTrue(proof["original_upstream_unmodified"])
        self.assertNotIn("qualified", proof)
        self.assertEqual(ORIGINAL["AC-17"], "INDETERMINATE_ORIGINAL_QHF_RETAINED")

    def test_changed_artifact_fails(self):
        self.addon.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "DIGEST_MISMATCH"):
            self.accepted()

    def test_wrong_source_commit_fails(self):
        self.r["source_commit"] = "0" * 40
        self.flush()
        with self.assertRaisesRegex(ValueError, "PINNED_SOURCE"):
            self.accepted()

    def test_dirty_source_fails(self):
        self.r["source_dirty"] = True
        self.flush()
        with self.assertRaisesRegex(ValueError, "PINNED_SOURCE"):
            self.accepted()

    def test_mismatched_manifest_fails(self):
        self.m["artifactSha256"] = "f" * 64
        self.flush()
        with self.assertRaisesRegex(ValueError, "DIGEST_MISMATCH"):
            self.accepted()

    def test_wrong_platform_fails(self):
        self.m["platform"] = "linux"
        self.flush()
        with self.assertRaisesRegex(ValueError, "WRONG_NATIVE_PACKAGE"):
            self.accepted()

    def test_missing_receipt_fails(self):
        self.receipt.unlink()
        with self.assertRaisesRegex(ValueError, "MISSING_ORIGINAL"):
            self.accepted()

    def test_oversized_receipt_fails(self):
        self.receipt.write_bytes(b"x" * 65537)
        with self.assertRaisesRegex(ValueError, "OVERSIZED_RECEIPT"):
            self.accepted()


if __name__ == "__main__":
    unittest.main()
