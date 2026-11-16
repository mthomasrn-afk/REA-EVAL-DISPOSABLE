import unittest
from judge import adjudicate

GOOD={"schema":"rea.owner.evidence.v0.1.0-candidate",
      "claimScope":"OWNER_ATTRIBUTED_NOT_INDEPENDENT",
      "completeAtSample":True,"pidListComplete":True,
      "pidError":0,"policyError":0,"accountingError":0,"identityError":0,
      "pidCap":64,"preResumeMembershipAsserted":True,"policyFlags":0x2000,
      "rootPid":11,"rootCreationFiletime":"1234567890",
      "preResumeQpc":"100","afterResumeQpc":"130",
      "queryQpcStart":"200","queryQpcEnd":"230","qpcFrequency":"10000000",
      "jobAssignedCount":3,"jobReturnedCount":3,
      "currentJobPids":[11,12,13],"totalProcesses":3,"activeProcesses":3,
      "totalTerminatedProcesses":0}
def result(payload):
    return adjudicate(payload,known_pids=[11,12,13],root_creation="1234567890",
                      outsider_pid=88,start_qpc=180,end_qpc=250)["disposition"]
class NegativeEvidenceTests(unittest.TestCase):
    def test_good_bounded(self):
        self.assertEqual(result(GOOD),"PASS_SCOPED_KNOWN_IDENTITIES")
    def test_wrong_schema(self):
        self.assertEqual(result({**GOOD,"schema":"faux"}),"FAIL")
    def test_false_independence(self):
        self.assertEqual(result({**GOOD,"claimScope":"FULL_C5_PASS"}),"FAIL")
    def test_incomplete(self):
        self.assertEqual(result({**GOOD,"pidListComplete":False}),"INDETERMINATE")
    def test_native_api_failure(self):
        self.assertEqual(result({**GOOD,"pidError":234}),"INDETERMINATE")
    def test_wrong_policy(self):
        self.assertEqual(result({**GOOD,"policyFlags":0}),"FAIL")
    def test_wrong_creation(self):
        self.assertEqual(result({**GOOD,"rootCreationFiletime":"999"}),"FAIL")
    def test_missing_known(self):
        self.assertEqual(result({**GOOD,"currentJobPids":[11,12],"jobReturnedCount":2,"jobAssignedCount":2}),"FAIL")
    def test_foreign_in_job(self):
        self.assertEqual(result({**GOOD,"currentJobPids":[11,12,13,88],"jobReturnedCount":4,
                                 "jobAssignedCount":4,"totalProcesses":4,"activeProcesses":4}),"FAIL")
    def test_extra_unverified(self):
        self.assertEqual(result({**GOOD,"currentJobPids":[11,12,13,77],"jobReturnedCount":4,
                                 "jobAssignedCount":4,"totalProcesses":4,"activeProcesses":4}),"INDETERMINATE")
    def test_independently_held_extra_earns_only_scoped_identity(self):
        x={**GOOD,"currentJobPids":[11,12,13,77],
           "jobReturnedCount":4,"jobAssignedCount":4,
           "totalProcesses":4,"activeProcesses":4}
        verdict=adjudicate(x,known_pids=[11,12,13],
                           root_creation="1234567890",outsider_pid=88,
                           start_qpc=180,end_qpc=250,witnessed_extra_pids=[77])
        self.assertEqual(verdict["disposition"],"PASS_SCOPED_REPORTED_IDENTITIES_WITH_EXTRAS")
        self.assertEqual(verdict["original_ac15"],"PARTIAL")
        self.assertEqual(verdict["original_topology"],"INDETERMINATE_UNEXPECTED_EXTRAS")
        self.assertFalse(verdict["complete_unknown_descendants_proven"])
    def test_partly_witnessed_extra_remains_indeterminate(self):
        x={**GOOD,"currentJobPids":[11,12,13,77,79],
           "jobReturnedCount":5,"jobAssignedCount":5,
           "totalProcesses":5,"activeProcesses":5}
        verdict=adjudicate(x,known_pids=[11,12,13],
                           root_creation="1234567890",outsider_pid=88,
                           start_qpc=180,end_qpc=250,witnessed_extra_pids=[77])
        self.assertEqual(verdict["disposition"],"INDETERMINATE")
    def test_query_outside_bracket(self):
        self.assertEqual(result({**GOOD,"queryQpcEnd":"310"}),"FAIL")
    def test_owner_clock_reversed(self):
        self.assertEqual(result({**GOOD,"queryQpcEnd":"190"}),"FAIL")
    def test_clock_missing(self):
        self.assertEqual(result({**GOOD,"qpcFrequency":None}),"INDETERMINATE")
    def test_assigned_count_mismatch(self):
        self.assertEqual(result({**GOOD,"jobAssignedCount":4}),"INDETERMINATE")
    def test_pre_resume_missing(self):
        self.assertEqual(result({**GOOD,"preResumeMembershipAsserted":False}),"FAIL")
    def test_accounting_too_low(self):
        self.assertEqual(result({**GOOD,"totalProcesses":2}),"FAIL")
    def test_duplicate_pid(self):
        self.assertEqual(result({**GOOD,"currentJobPids":[11,11,13]}),"FAIL")
    def test_pid_cap_rejected(self):
        self.assertEqual(result({**GOOD,"pidCap":0}),"FAIL")
if __name__=="__main__":unittest.main()
