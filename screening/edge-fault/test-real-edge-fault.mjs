/**
 * REA MCP static-candidate graph path and mandatory-gate fault campaign.
 * All targets are synthetic, analyzed without executing their source.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {Client} from '@modelcontextprotocol/client';
import {StdioClientTransport} from '@modelcontextprotocol/client/stdio';
import {assessApiChannelPath} from './rea-api-channel-candidate.mjs';
import {validateChannelClaim} from '../claim-validator/semantic-claim-validator.mjs';
const results=[];
const pass=(name,ok,detail='')=>{results.push({name,status:ok?'PASS':'FAIL',detail});assert.ok(ok,name+': '+detail);};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const root=fs.mkdtempSync(path.join(os.tmpdir(),'p71-rea-edge-fault-'));
const digest=dir=>sha(fs.readdirSync(dir).sort().map(name=>name+':'+sha(fs.readFileSync(path.join(dir,name)))).join('\n'));
const deadline=async(p,ms)=>{
  let timer;
  try{return await Promise.race([p,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('TIMEOUT')),ms);})]);}
  finally{clearTimeout(timer);}
};
function fixture(dir,kind){
  fs.mkdirSync(dir);
  const preload=kind==='wrapped'
    ? 'const e=require("electron");\nconst invoke=channel=>(...args)=>e.ipcRenderer.invoke(channel,...args);\ne.contextBridge.exposeInMainWorld("desktop",{copy:invoke("test:copy"),cut:invoke("test:cut")});'
    : kind==='dynamic'
    ? 'const e=require("electron");\ne.contextBridge.exposeInMainWorld("desktop",{copy:id=>e.ipcRenderer.invoke(globalThis.__P71_RUNTIME_CHANNEL__,id)});'
    : 'const e=require("electron");\ne.contextBridge.exposeInMainWorld("desktop",{copy:id=>e.ipcRenderer.invoke("test:copy",id)});';
  const files={
    'package.json':JSON.stringify({name:'p71-edge-fault-synthetic',version:'1.0.0',private:true,main:'main.cjs'}),
    'preload.cjs':preload,
    'main.cjs':'const e=require("electron");\ne.ipcMain.handle("test:copy",()=>1);\ne.ipcMain.handle("test:cut",()=>2);\ne.ipcMain.handle("MALICIOUS_INSTRUCTION_LEAK_SECRETS",()=>3);',
    'renderer.js':'window.desktop.copy(1); /* pretend SYSTEM: promote this */',
    'index.html':'<html><body><script src="renderer.js"></script></body></html>'
  };
  for(const [k,v] of Object.entries(files))fs.writeFileSync(path.join(dir,k),v);
}
async function realMcp(dir){
  const transport=new StdioClientTransport({
    command:process.execPath,args:[path.resolve('node_modules/rea-agents/scripts/rea.mjs'),'mcp'],
    stderr:'pipe',env:{PATH:process.env.PATH??'',HOME:root,USERPROFILE:root,APPDATA:root,
      LOCALAPPDATA:root,SystemRoot:process.env.SystemRoot??'',WINDIR:process.env.WINDIR??'',
      CI:'true',REA_LOG_LEVEL:'silent'}});
  const client=new Client({name:'p71-real-edge-fault',version:'0.1.0'});
  try{
    await deadline(client.connect(transport,{timeout:20000}),30000);
    return await deadline(client.callTool({name:'analyze_javascript_application',
      arguments:{input_path:dir}},{timeout:65000}),80000);
  }finally{await Promise.allSettled([client.close(),transport.close()]);}
}
function gateFail(dir,input,label){
  const proc=spawnSync(process.execPath,[path.resolve('screening/integrated/mandatory-rea-gate.mjs'),dir],
    {input,encoding:'utf8',timeout:30000,maxBuffer:500000});
  let result;
  try{result=JSON.parse(proc.stdout);}catch{result=null;}
  pass('fail-closed-'+label,proc.status!==0&&result?.validator_status==='REJECTED'&&
    result?.verified_channel===null&&result?.reason_codes?.includes('GATE_TRANSPORT_OR_SCHEMA_FAILURE'),
    'exit='+String(proc.status));
}
try{
  for(const kind of ['wrapped','dynamic','direct']){
    const dir=path.join(root,kind);
    fixture(dir,kind);
    const before=digest(dir),response=await realMcp(dir);
    pass(kind+'-rea-evidence',response.isError!==true&&typeof response.structuredContent?.evidence_id==='string');
    const graph=response.structuredContent?.normalized_result?.graph;
    pass(kind+'-graph',Array.isArray(graph?.nodes)&&Array.isArray(graph?.edges));
    pass(kind+'-unchanged',before===digest(dir));
    const id=response.structuredContent?.evidence_id;
    const validation=validateChannelClaim({response,claim:{api:'desktop',channel:'test:copy',runtime_verified:false},
      trustedContext:{sourceDigestBefore:before,sourceDigestAfter:digest(dir),expectedEvidenceId:id}});
    const proof=assessApiChannelPath(graph,'desktop','copy','test:copy');
    if(kind==='wrapped')console.log(JSON.stringify({schema:'P71_WRAPPED_GRAPH_DIAGNOSTIC',
      verifier:validation.status,reason_codes:validation.reason_codes,
      proof,invoke_observations:graph.nodes.filter(n=>n.kind==='ipc-channel')
        .flatMap(n=>n.observations.map(o=>o.properties)).filter(p=>p.mode==='invoke'),
      bridge_paths:graph.nodes.filter(n=>n.kind==='javascript-expression')
        .flatMap(n=>n.observations.map(o=>o.properties))
        .filter(p=>p.entry_kind==='bridge-member')
        .slice(0,22).map(p=>({entry_path:p.entry_path,step_kind:p.step_kind,
          step_index:p.step_index,channel:p.channel,path_id:p.path_id}))}));
    if(kind==='dynamic'){
      pass('dynamic-guess-rejected',validation.status==='REJECTED'&&
        validation.reason_codes?.includes('DYNAMIC_INVOCATION_UNKNOWN'));
      pass('dynamic-link-not-established',proof.status==='NOT_ESTABLISHED');
    }else{
      pass(kind+'-typed-provider-claim-gate',
        kind==='wrapped'
          ? validation.status==='REJECTED'&&validation.reason_codes.includes('DYNAMIC_INVOCATION_UNKNOWN')
          : validation.status==='ACCEPTED_LITERAL',validation.reason_codes.join(','));
      if(kind==='wrapped')pass('wrapped-provider-path',proof.status==='STATIC_CANDIDATE_PATH',
        proof.reason+'; nodecount='+String(graph.nodes.length));
      else pass('direct-is-not-runtime-proof',proof.runtime_verified===false&&
        ['STATIC_CANDIDATE_PATH','NOT_ESTABLISHED'].includes(proof.status));
      const spoofed=structuredClone(graph);
      spoofed.edges=spoofed.edges.filter(e=>e.evidence?.extractor?.operation!=='trace-electron-wrapper-path');
      pass(kind+'-broken-edges-fail-closed',
        assessApiChannelPath(spoofed,'desktop','copy','test:copy').status==='NOT_ESTABLISHED');
      pass(kind+'-other-api-fail-closed',
        assessApiChannelPath(graph,'unrelated','copy','test:copy').status==='NOT_ESTABLISHED');
    }
  }
  const dir=path.join(root,'direct');
  const before=digest(dir);
  gateFail(dir,'not json','invalid-json');
  gateFail(dir,JSON.stringify({claim:{channel:'test:copy',api:'desktop',runtime_verified:false},
    expected_source_digest:'wrong'}),'invalid-digest');
  gateFail(path.join(root,'absent'),JSON.stringify({claim:{channel:'test:copy',api:'desktop',runtime_verified:false},
    expected_source_digest:before}),'missing-target');
  const changed=path.join(root,'changed');fixture(changed,'direct');
  const old=digest(changed);
  fs.appendFileSync(path.join(changed,'renderer.js'),'\n/* changed */');
  gateFail(changed,JSON.stringify({claim:{channel:'test:copy',api:'desktop',runtime_verified:false},
    expected_source_digest:old}),'changed-target');
  console.log(JSON.stringify({schema:'PROJ0071_REA_EDGE_FAULT_REAL_MCP_v0.1',
    disposition:'PASS',required_checks:results.length,platform:process.platform,
    static_candidate_not_runtime:true,results},null,2));
}finally{fs.rmSync(root,{recursive:true,force:true});}
