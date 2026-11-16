// Existing ORIGINAL REA 6.5.0 native process_spawn owner drives REAL Concurrently.
// No new launcher/Job/controller; this test driver speaks only REA's native API.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {createRequire} from "node:module";
import {createInterface} from "node:readline";

if(process.platform!=="win32")throw Error("REAL_WINDOWS_REQUIRED");
const addon=process.argv[2],concurrent=process.argv[3];
if(!addon||!concurrent)throw Error("SOURCE_AND_NATIVE_REQUIRED");
const native=createRequire(import.meta.url)(path.resolve(addon));
const quote=v=>'"'+v.replace(/(\\*)"/gu,'$1$1\\"').replace(/(\\+)$/u,'$1$1')+'"';
const root=fs.mkdtempSync(path.join(os.tmpdir(),"rea-real-concurrently-"));
const filenames=[];
let launched,closed=false;
const wait=ms=>new Promise(ok=>setTimeout(ok,ms));
try{
  for(let n=1;n<=2;n++){
    const fp=path.join(root,"independent-real-command-"+n+".cjs");
    fs.writeFileSync(fp,"console.log('CONCURRENTLY_LIVE_"+n+"');"+
        "setTimeout(()=>process.exit(0),22000);\n");
    filenames.push(fp);
  }
  const childCommands=filenames.map(f=>quote(process.execPath)+" "+quote(f));
  const commandline=[quote(process.execPath),quote(path.resolve(concurrent)),
    "--raw",...childCommands.map(quote)].join(" ");
  const env=["SystemRoot","TEMP","TMP","PATH","COMSPEC"].filter(k=>process.env[k])
    .map(k=>k+"="+process.env[k]);
  launched=native.call("process_spawn",[process.execPath,commandline,root,env]);
  assert.equal(launched.jobAssigned,true);
  assert.equal(launched.killOnOwnerClose,true);
  let stdout="",last;
  for(let n=0;n<160;n++){
    last=native.call("process_poll",[launched.handle]);
    stdout+=last.stdout.toString();
    if(stdout.includes("CONCURRENTLY_LIVE_1")&&stdout.includes("CONCURRENTLY_LIVE_2")&&
       last.activeProcesses>=3)break;
    await wait(50);
  }
  assert.ok(stdout.includes("CONCURRENTLY_LIVE_1") &&
            stdout.includes("CONCURRENTLY_LIVE_2"),
            "GENUINE_CONCURRENTLY_DID_NOT_EXECUTE_BOTH_COMMANDS");
  assert.ok(last.activeProcesses>=3,"CHILD_PROCESS_JOB_POPULATION_NOT_OBSERVED");
  console.log("REAL_OWNER_READY "+JSON.stringify({root_pid:launched.pid,
    target:"unmodified_concurrently_10.0.7",real_output_markers:2,
    original_native_owner:true}));
  const reader=createInterface({input:process.stdin,crlfDelay:Infinity});
  const commands=reader[Symbol.asyncIterator]();
  for(let i=0;i<2;i++){
    assert.equal((await commands.next()).value,"observe");
    const s=native.call("process_evidence",[launched.handle]);
    console.log("REAL_OWNER_SAMPLE "+JSON.stringify(s));
  }
  assert.equal((await commands.next()).value,"go");
  reader.close();
  native.call("process_close",[launched.handle]);
  closed=true;
  console.log("REAL_OWNER_DONE "+JSON.stringify({owner_closed:true}));
}finally{
  if(launched&&!closed){
    try{native.call("process_terminate",[launched.handle])}catch{}
    try{native.call("process_close",[launched.handle])}catch{}
  }
  // Only the actor's own temporary two commands. No ambient files.
  try{fs.rmSync(root,{recursive:true,force:true})}catch{}
}
