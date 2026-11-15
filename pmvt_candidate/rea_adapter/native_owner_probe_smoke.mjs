// Hosted Windows synthetic native owner probe. No real REA provider or target.
// Explicitly NOT original C5/QHF/NEBQ native acceptance.
import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {spawnSync} from "node:child_process";
import {tmpdir} from "node:os";
import {resolve,dirname} from "node:path";
import {fileURLToPath} from "node:url";

if(process.platform!=="win32")throw Error("WINDOWS_NATIVE_REQUIRED");
const here=dirname(fileURLToPath(import.meta.url));
const native=createRequire(import.meta.url)(resolve(process.argv[2]));
const quote=s=>JSON.stringify(s);
const env=["SystemRoot","TEMP","TMP","PATH","COMSPEC"]
  .filter(k=>process.env[k]).map(k=>k+"="+process.env[k]);
const line=[process.execPath,"-e","setTimeout(()=>process.exit(0),2200)"].map(quote).join(" ");
const launched=native.call("process_spawn",[process.execPath,line,tmpdir(),env]);
assert.equal(launched.jobAssigned,true);
assert.equal(launched.killOnOwnerClose,true);
let closed=false;
try{
 const first=native.call("process_pmvt_owner_observation",[launched.handle]);
 assert.equal(first.schema,"rea.pmvt.owner-native.v0.1");
 assert.equal(first.pid,launched.pid);
 assert.equal(first.root_identity_observed,true);
 assert.equal(first.member_before_resume,true);
 assert.equal(first.resume_succeeded,true);
 assert.equal(first.kill_on_owner_close,true);
 assert.equal(first.breakaway_disabled,true);
 assert.ok(BigInt(first.creation_filetime_100ns)>0n);
 assert.ok(first.active_processes>=1);
 // PMVT obtains the same kernel identity in a DIFFERENT process without any
 // Job handle duplication. This proves only the root identity in this interval.
 const python=process.env.PYTHON||"python";
 const inspected=spawnSync(python,["-B",resolve(here,"../pmvt.py"),
    "observe-pid","--pid",String(launched.pid),"--run-id","ci-owned",
    "--duration-ms","25","--poll-ms","5"],{encoding:"utf8",timeout:15000});
 assert.equal(inspected.status,0,inspected.stderr);
 const observed=JSON.parse(inspected.stdout);
 assert.equal(observed.state,"ALIVE_AT_CUTOFF");
 assert.equal(observed.process_identity.creation_filetime_100ns,first.creation_filetime_100ns);
 let last;
 for(let i=0;i<160;i++){
   const state=native.call("process_poll",[launched.handle]);
   if(state.exitCode!==null && state.activeProcesses===0 && state.stdoutEnded && state.stderrEnded){
      last=native.call("process_pmvt_owner_observation",[launched.handle]);break;
   }
   await new Promise(r=>setTimeout(r,35));
 }
 assert.ok(last,"NATIVE_JOB_NOT_SETTLED_WITHIN_BOUND");
 assert.equal(last.active_processes,0);
 assert.equal(last.creation_filetime_100ns,first.creation_filetime_100ns);
 native.call("process_close",[launched.handle]); closed=true;
 assert.throws(()=>native.call("process_pmvt_owner_observation",[launched.handle]));
 const verify=spawnSync(python,["-B","-c",
  'import json,sys;sys.path.insert(0,sys.argv[1]);from rea_adapter.rea_owner_journal import build_journal;from pmvt import validate_owner_journal;x=json.load(sys.stdin);j=build_journal("ci-owned",x["first"],x["last"],cleanup_mode="normal",owner_released=True);v=validate_owner_journal(j);assert v["assertions"][0]["status"]=="PASS";assert v["rea_c5"]=="INDETERMINATE";print("OWNER_JOURNAL_CI_STRUCTURE_PASS")',
    resolve(here,"..")],{input:JSON.stringify({first,last}),encoding:"utf8",timeout:15000});
 assert.equal(verify.status,0,verify.stderr);
 console.log(JSON.stringify({schema:"pmvt.owner-candidate-ci.v0.1",scope:"SYNTHETIC_ONLY",
   state:"PASS",independent_root_identity:"MATCH",native_owner_journal:"STRUCTURE_PASS",
   job_handle_transferred:false,original_rea_c5:"INDETERMINATE"}));
}finally{
 if(!closed){try{native.call("process_terminate",[launched.handle])}catch{}
             try{native.call("process_close",[launched.handle])}catch{}}
}
