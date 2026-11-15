"""Strict REA-native-to-PMVT adapter negative controls; synthetic only."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rea_adapter.rea_owner_journal import build_journal
from rea_adapter.test_rea_owner_journal import snap
from rea_adapter.apply_rea_owner_probe import run, splice
from pmvt import validate_owner_journal

class AdapterHardening(unittest.TestCase):
    def test_native_flag_inconsistency(self):
        for changes in ({"job_limit_flags":0},{"job_limit_flags":0x2800},
                        {"kill_on_owner_close":False},{"breakaway_disabled":False}):
            with self.subTest(changes=changes),self.assertRaisesRegex(ValueError,"POLICY_FLAGS"):
                build_journal("bad-flags",snap(**changes))

    def test_resume_without_native_membership(self):
        with self.assertRaisesRegex(ValueError,"MEMBERSHIP"):
            build_journal("bad-member",snap(member_before_resume=False))

    def test_missing_birth_never_qualifies(self):
        j=build_journal("unknown-birth",snap(root_identity_observed=False,creation_filetime_100ns="0"))
        self.assertNotIn("child_resumed",[e["event"] for e in j["events"]])
        self.assertEqual(validate_owner_journal(j)["rea_c5"],"INDETERMINATE")

    def test_incomplete_cancel_never_settles(self):
        j=build_journal("cancel",snap(),snap(active_processes=2,total_processes=3),cleanup_mode="cancel")
        self.assertNotIn("job_settled",[e["event"] for e in j["events"]])

    def test_impossible_terminated_accounting(self):
        with self.assertRaisesRegex(ValueError,"INCONSISTENT_ACCOUNTING"):
            build_journal("bad-count",snap(total_processes=1,total_terminated_processes=3))

    def test_private_unknown_field(self):
        with self.assertRaisesRegex(ValueError,"EXTRA_FIELD"):
            build_journal("private",snap(command_line="SECRET"))

    def test_exact_source_patch_guards(self):
        with self.assertRaisesRegex(RuntimeError,"REQUIRES_PINNED_GIT_CLONE"):
            run(Path(__file__).resolve().parents[1],True)
        for source,old in (("","x"),("abc","z"),("aaaa","aa")):
            with self.assertRaisesRegex(RuntimeError,"SOURCE_ANCHOR_MISMATCH"):
                splice(source,old,"new","negative")
