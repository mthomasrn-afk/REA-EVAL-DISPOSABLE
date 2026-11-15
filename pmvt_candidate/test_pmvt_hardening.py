"""Negative/privacy hardening for untrusted owner claims; no REA C5 authority."""
import copy
import unittest
from pmvt import validate_owner_journal
from test_pmvt import sample

class Hardening(unittest.TestCase):
    def test_private_fields_in_each_event(self):
        for index in range(7):
            for key in ("command_line", "environment", "private_path", "bearer_token"):
                j = sample()
                j["events"][index]["data"][key] = "SECRET"
                with self.subTest(index=index,key=key):
                    self.assertEqual(validate_owner_journal(j)["assertions"][0]["status"], "FAIL")

    def test_job_policy_negative(self):
        for key in ("kill_on_owner_close", "breakaway_disabled"):
            j = sample()
            j["events"][0]["data"][key] = False
            v = validate_owner_journal(j)
            self.assertEqual(v["rea_c5"], "NOT_QUALIFIED")
            self.assertIn("FAIL", [a["status"] for a in v["assertions"]])

    def test_conflicting_job_flags(self):
        for flags, kill, breakaway in ((0,True,True),(0x2000,False,True),
                                        (0x2800,True,True),(0x2000,True,False)):
            j = sample()
            j["events"][0]["data"].update(job_limit_flags=flags,kill_on_owner_close=kill,breakaway_disabled=breakaway)
            with self.subTest(flags=flags):
                self.assertEqual(validate_owner_journal(j)["assertions"][0]["status"], "FAIL")

    def test_consistent_unsafe_policy_still_negative(self):
        j = sample()
        j["events"][0]["data"].update(job_limit_flags=0,kill_on_owner_close=False,breakaway_disabled=True)
        v = validate_owner_journal(j)
        self.assertEqual(v["assertions"][0]["status"], "PASS")
        self.assertEqual(v["rea_c5"], "NOT_QUALIFIED")

    def test_cleanup_boundary_cannot_be_invented(self):
        j = sample()
        j["events"].pop(4)
        for n,e in enumerate(j["events"],1): e["seq"] = n
        self.assertEqual(validate_owner_journal(j)["assertions"][0]["status"],"FAIL")

    def test_invalid_creation_identifiers(self):
        for created in ("1"*2000,"18446744073709551616","0000","inf"):
            j = sample()
            for i in (1,2,3): j["events"][i]["data"]["creation_filetime_100ns"] = created
            with self.subTest(created=created[:25]):
                self.assertEqual(validate_owner_journal(j)["assertions"][0]["status"],"FAIL")

    def test_partials_and_forged_order_time_not_acceptance(self):
        j=sample(); j["events"]=j["events"][:2]
        self.assertEqual(validate_owner_journal(j)["rea_c5"],"INDETERMINATE")
        j=sample()
        for i,e in enumerate(j["events"]): e["t_ns"]=900000000000000+i
        self.assertEqual(validate_owner_journal(j)["rea_c5"],"INDETERMINATE")

    def test_malformed_record_matrix(self):
        j=sample()
        for i in range(7):
            for field,bad in (("run_id","WRONG"),("seq",0),("t_ns",True),("data",[])):
                x=copy.deepcopy(j)
                x["events"][i][field]=bad
                with self.subTest(index=i,field=field):
                    self.assertEqual(validate_owner_journal(x)["assertions"][0]["status"],"FAIL")
