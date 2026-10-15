/**
 * PROJ-0071 mandatory gate adapter for real local-model LangGraph candidate.
 * This process—not the model—obtains fresh REA MCP evidence and source hashes.
 * stdin contains only the model claim and a prior trusted source inventory digest.
 * No source content or standalone model-provided evidence is treated as authority.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';
import { validateChannelClaim } from '../claim-validator/semantic-claim-validator.mjs';

const target=process.argv[2];
const isHash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const inventory=directory=>{
  const entries=[];
  function visit(dir,prefix=''){
    for(const e of fs.readdirSync(dir,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))){
      const rel=prefix?prefix+'/'+e.name:e.name,filename=path.join(dir,e.name);
      if(e.isDirectory())visit(filename,rel);
      else if(e.isFile())entries.push(rel+':'+hash(fs.readFileSync(filename)));
      else throw Error('UNSUPPORTED_FIXTURE_ENTRY');
    }
  }
  visit(directory);
  return hash(entries.sort().join('\n'));
};
const deadline=async(p,ms)=>{let timer;try{return await Promise.race([p,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('TIMEOUT')),ms)})]);}finally{clearTimeout(timer);}};
let transport,client;
try{
  if(!path.isAbsolute(target)||!fs.statSync(target).isDirectory())throw Error('INVALID_TARGET');
  const incoming=JSON.parse(fs.readFileSync(0,'utf8'));
  if(!incoming||!isHash(incoming.expected_source_digest))throw Error('INVALID_TRUSTED_INPUT');
  const before=inventory(target);
  if(before!==incoming.expected_source_digest)throw Error('SOURCE_CHANGED_SINCE_MODEL_OBSERVATION');
  const env={PATH:process.env.PATH||'', HOME:process.env.HOME||'',
    USERPROFILE:process.env.USERPROFILE||'',APPDATA:process.env.APPDATA||'',
    LOCALAPPDATA:process.env.LOCALAPPDATA||'',SystemRoot:process.env.SystemRoot||'',
    WINDIR:process.env.WINDIR||'',CI:'true',REA_LOG_LEVEL:'silent'};
  transport=new StdioClientTransport({command:process.execPath,
    args:[path.resolve('node_modules/rea-agents/scripts/rea.mjs'),'mcp'],env,stderr:'pipe'});
  client=new Client({name:'p71-gated-consumer-proof',version:'0.1.0'});
  await deadline(client.connect(transport,{timeout:20000}),30000);
  const response=await deadline(client.callTool({
    name:'analyze_javascript_application',arguments:{input_path:target}
  },{timeout:65000}),80000);
  const after=inventory(target);
  const trustedContext={sourceDigestBefore:before,sourceDigestAfter:after,
    expectedEvidenceId:response.structuredContent?.evidence_id??null};
  const verdict=validateChannelClaim({response,claim:incoming.claim,trustedContext});
  const output={schema:'P71_REA_MANDATORY_VERIFICATION_v0.1.0',
    validator_status:verdict.status,
    verified_channel:verdict.verified_channel??null,
    provenance:verdict.provenance,
    reason_codes:verdict.reason_codes,
    source_unchanged:before===after,
    rejected_claim:verdict.rejected_claim,
    checks:{trusted_inventory_matched:before===incoming.expected_source_digest,
      evidence_identity_checked:verdict.provenance?.evidence_id!==null,
      actual_rea_mcp:true,worker_authority:'single_read_only_analysis_tool'}};
  console.log(JSON.stringify(output));
} catch(error){
  // No claim or source content can escape on infrastructure failure.
  console.log(JSON.stringify({schema:'P71_REA_MANDATORY_VERIFICATION_v0.1.0',
    validator_status:'REJECTED',verified_channel:null,
    provenance:null,reason_codes:['GATE_TRANSPORT_OR_SCHEMA_FAILURE'],
    source_unchanged:false,rejected_claim:null,
    checks:{actual_rea_mcp:false,worker_authority:'single_read_only_analysis_tool'}}));
  process.exitCode=1;
}finally{
  await Promise.allSettled([client?.close(),transport?.close()]);
}
