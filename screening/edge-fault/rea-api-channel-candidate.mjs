/**
 * PROJ-0071 candidate relationship proof: exact source-bound static inference.
 *
 * This deliberately does NOT promote a call-path observation to verified runtime.
 * It recognizes only REA's explicit application-graph call-path chain, not
 * co-occurring API and IPC strings or matching main-process handlers.
 */
const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const text=x=>typeof x==='string'&&x.length>0&&x.length<=512;
export function assessApiChannelPath(graph,api,member,channel) {
  const none=(reason,details={})=>({status:'NOT_ESTABLISHED',reason,api,member,channel,
    runtime_verified:false,scope:'static-candidate-only',...details});
  if(!obj(graph)||!Array.isArray(graph.nodes)||!Array.isArray(graph.edges)||
    graph.nodes.length>100000||graph.edges.length>200000||!text(api)||!text(member)||
    !text(channel))return none('GRAPH_OR_QUERY_INVALID');
  const nodes=new Map();
  for(const n of graph.nodes) {
    if(!obj(n)||!text(n.node_id)||nodes.has(n.node_id))return none('NODE_SET_INVALID');
    nodes.set(n.node_id,n);
  }
  const matches=new Map();
  for(const n of graph.nodes){
    if(n.kind!=='javascript-expression')continue;
    if(!Array.isArray(n.observations))return none('OBSERVATION_INVALID');
    for(const o of n.observations){
      const p=o?.properties;
      if(!obj(p)||p.entry_kind!=='bridge-member'||!text(p.path_id)||
        !Array.isArray(p.entry_path)||p.entry_path.length<2||
        p.entry_path[0]!==api||p.entry_path[1]!==member||
        p.resolution!=='candidate')continue;
      if(p.entry_path.length!==2)continue;
      if(p.channel!==channel||p.conditions?.length)continue;
      const slot=matches.get(p.path_id)||[];
      slot.push({node_id:n.node_id,step:p.step_kind,index:p.step_index,
        path_id:p.path_id,observation:o,channel:p.channel});
      matches.set(p.path_id,slot);
    }
  }
  const supported=[];
  for(const [pathId,steps] of matches) {
    steps.sort((a,b)=>a.index-b.index);
    if(steps.length<2||steps[0].index!==0||steps[0].step!=='exposure'||
       steps[steps.length-1].step!=='terminal'||
       steps.some((s,i)=>!Number.isInteger(s.index)||s.index!==i))continue;
    let complete=true;
    for(let i=1;i<steps.length;i++){
      const left=steps[i-1],right=steps[i];
      const edges=graph.edges.filter(e=>obj(e)&&e.source_node_id===left.node_id&&
        e.target_node_id===right.node_id&&
        e.evidence?.extractor?.operation==='trace-electron-wrapper-path'&&
        e.properties?.path_id===pathId&&e.properties?.resolution==='candidate'&&
        (e.relation==='calls'||e.relation==='maps_to'));
      if(edges.length!==1){complete=false;break;}
    }
    if(complete)supported.push({path_id:pathId,steps:steps.length,channel});
  }
  if(supported.length!==1)return none(supported.length?'AMBIGUOUS_CANDIDATE_PATHS':'NO_UNIQUE_COMPLETE_PATH',
    {candidate_count:supported.length});
  // Graph-level channel observation must agree with this path, but does not
  // on its own establish which exposed API causes the IPC transmission.
  const witnesses=graph.nodes.filter(n=>n.kind==='ipc-channel').flatMap(n=>
    Array.isArray(n.observations)?n.observations.map(o=>o?.properties):[]).filter(
      p=>p?.mode==='invoke'&&p.channel===channel);
  if(witnesses.length<1)return none('NO_TYPED_INVOKE_WITNESS');
  return {status:'STATIC_CANDIDATE_PATH',reason:'SOURCE_BOUND_INFERRED_PATH',
    api,member,channel,path_id:supported[0].path_id,steps:supported[0].steps,
    static_inference_only:true,runtime_verified:false,
    api_channel_link:'CANDIDATE_NOT_RUNTIME_VERIFIED',
    scope:'static-candidate-only'};
}
