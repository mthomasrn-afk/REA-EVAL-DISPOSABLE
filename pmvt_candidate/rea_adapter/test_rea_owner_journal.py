"""Synthetic paired-negative tests; no REA/Factory qualification implied."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pmvt import validate_owner_journal
from rea_adapter.rea_owner_journal import build_journal

def sample(**kw):
    s={"schema":"rea.pmvt.owner-native.v0.1","pid":31415,
       "creation_filetime_100ns":"133772222222222222","root_identity_observed":True,
       "member_before_resume":True,"resume_succeeded":True,
       "job_limit_flags":8192,"kill_on_owner_close":True,"breakaway_disabled":True,
       "active_processes":1,"total_processes":1,"total_terminated_processes":0}
    s.update(kw)
    return s

class OwnerAdapterTests(unittest.TestCase):
    def test_positive_start_never_c5(self):
        j=build_journal("synthetic",sample()); v=validate_owner_journal(j)
        self.assertEqual(v["assertions"][0]["status"],"PASS")
        self.assertEqual(v["rea_c5"],"INDETERMINATE")
    def test_positive_clean_end_never_c5(self):
        j=build_journal("synthetic",sample(),sample(active_processes=0,total_processes=2),cleanup_mode="normal",owner_released=True)
        v=validate_owner_journal(j)
        self.assertEqual(len(j["events"]),7)
        self.assertEqual(v["rea_c5"],"INDETERMINATE")
    def test_no_complete_claim_for_partial(self):
        self.assertNotIn("job_settled", [x["event"] for x in build_journal("x",sample())["events"]])
    def test_unsettled_does_not_emit_settlement(self):
        j=build_journal("x",sample(),sample(active_processes=1),cleanup_mode="timeout")
        self.assertNotIn("job_settled",[x["event"] for x in j["events"]])
    def test_missing_root_identity_does_not_invent_resume(self):
        j=build_journal("x",sample(root_identity_observed=False,creation_filetime_100ns="0"))
        self.assertNotIn("child_resumed",[x["event"] for x in j["events"]])
    def test_failed_membership_is_negative(self):
        j=build_journal("x",sample(member_before_resume=False,resume_succeeded=False))
        self.assertNotIn("child_resumed",[x["event"] for x in j["events"]])
        self.assertTrue(any(x["status"]=="FAIL" for x in validate_owner_journal(j)["assertions"]))
    def test_second_program_reuse(self):
        self.assertEqual(validate_owner_journal(build_journal("other-tool",sample()))["rea_c5"],"INDETERMINATE")
    def test_no_exact_job_handle_in_output(self):
        self.assertNotIn("job_ref",repr(build_journal("x",sample())))
    def test_reject_sensitive_extra_field(self):
        with self.assertRaises(ValueError):build_journal("x",sample(command_line="SECRET"))
    def test_reject_cross_pid(self):
        with self.assertRaises(ValueError):build_journal("x",sample(),sample(pid=77),cleanup_mode="normal")
    def test_reject_pid_reuse(self):
        with self.assertRaises(ValueError):build_journal("x",sample(),sample(creation_filetime_100ns="133772222222222223"),cleanup_mode="normal")
    def test_reject_reversed_counters(self):
        with self.assertRaises(ValueError):build_journal("x",sample(total_processes=3),sample(total_processes=2),cleanup_mode="normal")
    def test_reject_unsupported_owner_release(self):
        with self.assertRaises(ValueError):build_journal("x",sample(),sample(active_processes=1),cleanup_mode="normal",owner_released=True)
    def test_reject_release_without_final(self):
        with self.assertRaises(ValueError):build_journal("x",sample(),owner_released=True)
    def test_cleanup_cause_required(self):
        with self.assertRaises(ValueError):build_journal("x",sample(),sample(active_processes=0))
    def test_boolean_numeric_rejected(self):
        with self.assertRaises(ValueError):build_journal("x",sample(active_processes=False))
    def test_boolean_membership_rejected(self):
        with self.assertRaises(ValueError):build_journal("x",sample(member_before_resume="true"))
    def test_no_spaces_in_runid(self):
        with self.assertRaises(ValueError):build_journal("secret run",sample())
    def test_contradictory_creation_rejected(self):
        with self.assertRaises(ValueError):build_journal("x",sample(root_identity_observed=True,creation_filetime_100ns="0"))
    def test_accounting_inconsistent_rejected(self):
        with self.assertRaises(ValueError):build_journal("x",sample(total_processes=0))
if __name__=="__main__":unittest.main()
