// Disposable REA Windows-native owner fixture; NOT PMVT process-control code.
import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {tmpdir} from "node:os";
import {resolve} from "node:path";

if(process.platform!=="win32"||process.argv.length!==4)throw Error("WINDOWS_FIXTURE_ARGUMENTS_REQUIRED");
const native=createRequire(import.meta.url)(resolve(process.argv[2]));
const mode=process.argv[3];
if(!["natural","terminate","close","crash"].includes(mode))throw Error("UNKNOWN_FIXTURE_MODE");
const quote=value=>'"'+value.replace(/(\\*)"/gu,'$1$1\\"').replace(/(\\+)$/u,'$1$1')+'"';
const lifetimeMs=mode==="natural"?3500:15000;
const code=[
  "const {spawn}=require('node:child_process')",
  "const ms="+lifetimeMs,
  "const child=spawn(process.execPath,['-e','setTimeout(()=>process.exit(0),'+ms+')'],{stdio:'ignore',windowsHide:true})",
  "if(!Number.isInteger(child.pid)||child.pid<=0)process.exit(41)",
  "console.log('PMVT_DESC='+child.pid)",
  "setTimeout(()=>process.exit(0),ms)"
].join(";");
const command=[process.execPath,"-e",code].map(quote).join(" ");
const env=["SystemRoot","TEMP","TMP","PATH","COMSPEC"].filter(x=>process.env[x]).map(x=>x+"="+process.env[x]);
const launch=native.call("process_spawn",[process.execPath,command,tmpdir(),env]);
const handle=launch.handle;
let closed=false;
const sleep=t=>new Promise(r=>setTimeout(r,t));
const snapshot=()=>native.call("process_pmvt_owner_observation",[handle]);
async function settle(){
  for(let i=0;i<220;i++){
    const s=native.call("process_poll",[handle]);
    if(s.exitCode!==null&&s.activeProcesses===0&&s.stdoutEnded&&s.stderrEnded)return s;
    await sleep(25);
  }
  throw Error("JOB_DID_NOT_SETTLE_IN_SYNTHETIC_BOUND");
}
try{
  assert.equal(launch.jobAssigned,true);
  assert.equal(launch.killOnOwnerClose,true);
  let desc=0,first;
  for(let i=0;i<220;i++){
    const s=native.call("process_poll",[handle]);
    const match=s.stdout.toString().match(/PMVT_DESC=(\d+)/u);
    if(match)desc=Number(match[1]);
    first=snapshot();
    if(desc>0&&first.active_processes>=2)break;
    await sleep(25);
  }
  assert.ok(desc>0&&first.active_processes>=2,"FIXTURE_DESCENDANT_MISSING");
  assert.equal(first.member_before_resume,true);
  assert.equal(first.kill_on_owner_close,true);
  assert.equal(first.breakaway_disabled,true);
  console.log("PMVT_READY "+JSON.stringify({mode:mode,root_pid:launch.pid,descendant_pid:desc,owner_snapshot:first}));
  const cmd=await new Promise(resolve=>process.stdin.once("data",b=>resolve(String(b).trim())));
  assert.equal(cmd,"proceed");
  process.stdin.destroy(); // Never keep the disposable owner alive after command.
  if(mode==="crash")throw Error("CRASH_MODE_REQUIRES_EXTERNAL_OWNER_KILL");
  if(mode==="terminate"){
    assert.equal(native.call("process_terminate",[handle]),true);
    await settle();
  }
  if(mode==="natural")await settle();
  if(mode==="close"){
    assert.ok(snapshot().active_processes>=1,"NO_LIVE_MEMBER_FOR_CLOSE");
    native.call("process_close",[handle]);closed=true;
  }else{
    assert.equal(snapshot().active_processes,0);
    native.call("process_close",[handle]);closed=true;
  }
  console.log("PMVT_DONE "+JSON.stringify({mode:mode,state:"OWNER_RETURNED"}));
}finally{
  if(!closed){
    try{native.call("process_terminate",[handle]);}catch{}
    try{native.call("process_close",[handle]);}catch{}
  }
}
