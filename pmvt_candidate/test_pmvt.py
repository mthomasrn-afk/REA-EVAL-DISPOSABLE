"""Synthetic controls only; PASS means narrow software assertions, never REA C5."""
import os
import unittest

from pmvt import SCHEMA, observe_pid, validate_owner_journal


def sample():
    kinds = [
        ("job_created", {"job_ref": "synthetic-job-A"}),
        ("child_suspended", {"pid": 31415, "creation_filetime_100ns": "123456789"}),
        ("membership_checked", {"pid": 31415, "creation_filetime_100ns": "123456789", "member": True}),
        ("child_resumed", {"pid": 31415, "creation_filetime_100ns": "123456789"}),
        ("cleanup_started", {"mode": "normal"}),
        ("job_settled", {"active_processes": 0}),
        ("owner_released", {}),
    ]
    return {"schema": SCHEMA, "run_id": "synthetic-a", "events": [
        {"seq": i, "run_id": "synthetic-a", "t_ns": i * 1000, "event": kind, "data": data}
        for i, (kind, data) in enumerate(kinds, 1)
    ]}


def status(result, claim):
    return next(a["status"] for a in result["assertions"] if a["claim"] == claim)


class OwnerJournalTests(unittest.TestCase):
    def test_structural_positive_never_proves_c5(self):
        v = validate_owner_journal(sample())
        self.assertEqual(status(v, "journal_structure"), "PASS")
        self.assertEqual(status(v, "exact_job_membership"), "INDETERMINATE")
        self.assertEqual(status(v, "complete_settlement"), "INDETERMINATE")
        self.assertEqual(status(v, "temporal_descendant_coverage"), "INDETERMINATE")
        self.assertEqual(v["rea_c5"], "INDETERMINATE")

    def test_missing_final_record_fails_closed(self):
        s = sample(); s["events"] = s["events"][:4]
        v = validate_owner_journal(s)
        self.assertEqual(v["rea_c5"], "INDETERMINATE")
        self.assertEqual(status(v, "complete_settlement"), "INDETERMINATE")

    def test_owner_reports_nonmembership(self):
        s = sample(); s["events"][2]["data"]["member"] = False
        self.assertEqual(status(validate_owner_journal(s), "owner_reported_membership"), "FAIL")

    def test_owner_reports_unsettled(self):
        s = sample(); s["events"][5]["data"]["active_processes"] = 2
        self.assertEqual(status(validate_owner_journal(s), "owner_reported_settlement"), "FAIL")

    def test_negative_schema(self):
        s = sample(); s["schema"] = "not-pmvt"
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_run_binding(self):
        s = sample(); s["events"][3]["run_id"] = "other"
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_sequence_gap(self):
        s = sample(); s["events"][3]["seq"] = 99
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_reordered_resume(self):
        s = sample()
        s["events"][2]["event"], s["events"][3]["event"] = "child_resumed", "membership_checked"
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_clock(self):
        s = sample(); s["events"][3]["t_ns"] = 1
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_process_mismatch(self):
        s = sample(); s["events"][2]["data"]["pid"] = 31416
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_pid_reuse_at_membership(self):
        s = sample(); s["events"][2]["data"]["creation_filetime_100ns"] = "987654321"
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_missing_kernel_creation_identity(self):
        s = sample(); del s["events"][1]["data"]["creation_filetime_100ns"]
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_second_program_generic_contract(self):
        s = sample(); s["run_id"] = "synthetic-other-program"
        for e in s["events"]: e["run_id"] = s["run_id"]
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "PASS")

    def test_negative_boolean_as_pid(self):
        s = sample(); s["events"][1]["data"]["pid"] = True
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_release_without_settlement(self):
        s = sample(); s["events"].pop(5)
        for i, e in enumerate(s["events"], 1): e["seq"] = i
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_duplicate_event(self):
        s = sample(); s["events"][3]["event"] = "membership_checked"
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_invalid_numeric_active(self):
        s = sample(); s["events"][5]["data"]["active_processes"] = True
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")

    def test_negative_extra_field(self):
        s = sample(); s["events"][0]["environment_secrets"] = "forbidden"
        self.assertEqual(status(validate_owner_journal(s), "journal_structure"), "FAIL")


class NativeObservationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows-only native test")
    def test_live_self_pid_identity_and_bounded_wait(self):
        o = observe_pid("synthetic-self", os.getpid(), 35, 10)
        self.assertEqual(o["state"], "ALIVE_AT_CUTOFF")
        self.assertTrue(o["retained_process_handle"])
        self.assertGreater(int(o["process_identity"]["creation_filetime_100ns"]), 0)
        self.assertEqual(o["acceptance"], "NOT_ASSESSED")

    @unittest.skipUnless(os.name == "nt", "Windows-only native test")
    def test_missing_pid_inadmissible(self):
        o = observe_pid("synthetic-missing", 0xffffffff, 15, 5)
        self.assertEqual(o["state"], "INDETERMINATE")
        self.assertEqual(o["reason"], "OPEN_PROCESS_FAILED")

    def test_unsupported_platform_or_bounds(self):
        o = observe_pid("synthetic-test", 123, 0, 1)
        if os.name != "nt": self.assertEqual(o["state"], "NOT_RUN")
        else: self.assertIn(o["state"], ("INDETERMINATE", "EXITED_WITHIN_INTERVAL", "ALIVE_AT_CUTOFF"))

    @unittest.skipUnless(os.name == "nt", "Windows-only native test")
    def test_no_unbounded_wait(self):
        o = observe_pid("synthetic-test", os.getpid(), 25000, 10)
        self.assertEqual(o["reason"], "INVALID_BOUNDS")


if __name__ == "__main__":
    unittest.main()
