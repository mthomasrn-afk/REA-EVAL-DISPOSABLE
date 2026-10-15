/**
 * PROJ-0071 REA semantic-claim validator v0.1.0.
 * Deterministic candidate only, NOT a qualified security or authority boundary.
 * IMPORTANT: MCP response and trustedContext must come from trusted runner plumbing,
 * never from the model or from user-supplied source data.
 * Scope: artifact-wide IPC invocation; relation to a particular bridge API
 * is NOT established by this validator.
 */
const obj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const sha=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
const str=v=>typeof v==='string'&&v.length>0&&v.length<=512;
export function validateChannelClaim({response,claim,trustedContext}={}){
  const provenance={evidence_id:null,source_sha256:null,untrusted_source:true,
    graph_scope:'artifact-global',api_channel_link:'NOT_ESTABLISHED'};
  const observed={invocation_count:0,literal_invocations:[],dynamic_invocation_count:0,handler_only_channels:[]};
  const base={schema:'PROJ0071_REA_SEMANTIC_CLAIM_v0.1.0',provenance,observed};
  const rejected_claim=obj(claim)?{
    channel:claim.channel??null,api:claim.api??null,
    runtime_verified:claim.runtime_verified??null
  }:null;
  const reject=(...reason_codes)=>({...base,status:'REJECTED',resolution:'UNKNOWN',
    verified_channel:null,rejected_claim,reason_codes});
  if(!obj(trustedContext)||!sha(trustedContext.sourceDigestBefore)||
     !sha(trustedContext.sourceDigestAfter)||!str(trustedContext.expectedEvidenceId))
    return reject('TRUSTED_CONTEXT_INVALID');
  provenance.source_sha256=trustedContext.sourceDigestBefore;
  if(trustedContext.sourceDigestBefore!==trustedContext.sourceDigestAfter)
    return reject('SOURCE_MUTATED');
  if(!obj(response)||response.isError===true||!obj(response.structuredContent)||
     !obj(response.structuredContent.normalized_result))
    return reject('REA_MCP_EVIDENCE_INVALID');
  const evidence=response.structuredContent;
  provenance.evidence_id=str(evidence.evidence_id)?evidence.evidence_id:null;
  if(evidence.evidence_id!==trustedContext.expectedEvidenceId)
    return reject('EVIDENCE_IDENTITY_MISMATCH');
  if(response._meta?.provenance?.untrusted_content!==true)
    return reject('REA_UNTRUSTED_MARKER_MISSING');
  const nodes=evidence.normalized_result.graph?.nodes;
  if(!Array.isArray(nodes)||nodes.length>100000||nodes.some(n=>!obj(n)))
    return reject('REA_GRAPH_INVALID');
  const invokes=[],handlers=[],apis=[];
  for(const node of nodes){
    if(node.kind!=='ipc-channel'&&node.kind!=='context-bridge-api')continue;
    if(!Array.isArray(node.observations)||node.observations.length>20000)
      return reject('REA_OBSERVATIONS_INVALID');
    for(const ob of node.observations){
      if(!obj(ob)||!obj(ob.properties))return reject('REA_OBSERVATIONS_INVALID');
      const p=ob.properties;
      if(node.kind==='context-bridge-api'){
        if(str(p.api_key))apis.push(p.api_key);
      }else if(p.mode==='invoke'){
        if(p.channel!==null&&p.channel!==undefined&&!str(p.channel))
          return reject('INVOCATION_CHANNEL_INVALID');
        invokes.push({channel:p.channel??null,resolution:p.resolution??null});
      }else if((p.mode==='handle'||p.mode==='listen')&&str(p.channel)){
        handlers.push(p.channel);
      }
    }
  }
  const literals=[...new Set(invokes.map(i=>i.channel).filter(i=>i!==null))].sort();
  observed.invocation_count=invokes.length;
  observed.literal_invocations=literals.slice(0,40);
  observed.dynamic_invocation_count=invokes.filter(i=>i.channel===null||i.resolution==='dynamic').length;
  observed.handler_only_channels=[...new Set(handlers.filter(h=>!literals.includes(h)))].sort().slice(0,40);
  if(!obj(claim)||!str(claim.api)||
    !(claim.channel===null||(typeof claim.channel==='string'&&claim.channel.length<=512))||
    typeof claim.runtime_verified!=='boolean')return reject('MODEL_CLAIM_INVALID');
  if(claim.runtime_verified!==false)return reject('RUNTIME_UNVERIFIED');
  if(!apis.includes(claim.api))return reject('API_KEY_NOT_IN_REA_GRAPH');
  if(invokes.length===0)return reject('NO_INVOCATION_EVIDENCE');
  const unknown=claim.channel===null||claim.channel===''||
    claim.channel==='unknown'||claim.channel==='UNKNOWN';
  const dynamic=observed.dynamic_invocation_count>0;
  if(dynamic||literals.length!==1){
    if(!unknown)return reject(
      dynamic?'DYNAMIC_INVOCATION_UNKNOWN':'AMBIGUOUS_INVOCATIONS',
      'UNSUPPORTED_LITERAL_CLAIM',
      handlers.includes(claim.channel)&&!literals.includes(claim.channel)
        ?'HANDLER_REGISTRATION_NOT_INVOCATION':'NO_EXACT_INVOKE_WITNESS');
    return {...base,status:'ACCEPTED_UNKNOWN',resolution:'UNKNOWN',
      verified_channel:null,rejected_claim:null,
      reason_codes:[dynamic?'DYNAMIC_INVOCATION_UNKNOWN':'AMBIGUOUS_INVOCATIONS']};
  }
  if(unknown||claim.channel!==literals[0])return reject(
    'CLAIM_NOT_SUPPORTED_BY_LITERAL_INVOKE',
    handlers.includes(claim.channel)&&!literals.includes(claim.channel)
      ?'HANDLER_REGISTRATION_NOT_INVOCATION':'INCORRECT_OR_UNDERCLAIMED_CHANNEL');
  return {...base,status:'ACCEPTED_LITERAL',resolution:'LITERAL',
    verified_channel:literals[0],rejected_claim:null,
    reason_codes:['EXACT_TYPED_INVOKE_WITNESS']};
}
