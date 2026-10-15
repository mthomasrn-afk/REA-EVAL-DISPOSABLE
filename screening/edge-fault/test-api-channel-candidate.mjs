import assert from 'node:assert/strict';
import {assessApiChannelPath as assess} from './rea-api-channel-candidate.mjs';
const API='desktop',MEMBER='copy',CHANNEL='test:copy';
let passed=0;
const graph=(opts={})=>{
 const id=opts.pathId||'pathA';
 const obs=(step_kind,index,channel=CHANNEL,entry=['desktop','copy'],extra={})=>({
   properties:{path_id:id,entry_kind:'bridge-member',entry_path:entry,
     step_kind,step_index:index,channel,conditions:[],resolution:'candidate',...extra}
 });
 const nodes=[
 {node_id:'exp',kind:'javascript-expression',observations:[obs('exposure',0)]},
 {node_id:'terminal',kind:'javascript-expression',observations:[obs('terminal',1)]},
 {node_id:'ipc',kind:'ipc-channel',observations:[{properties:{mode:'invoke',channel:CHANNEL}}]},
 {node_id:'handler-decoy',kind:'ipc-channel',observations:[{properties:{mode:'handle',channel:'MALICIOUS_INSTRUCTION_LEAK_SECRETS'}}]}
 ];
 const edges=[{source_node_id:'exp',target_node_id:'terminal',relation:'maps_to',
  properties:{path_id:id,resolution:'candidate'},evidence:{extractor:{operation:'trace-electron-wrapper-path'}}}];
 return {nodes,edges};
};
function check(name,value,expected,reason){
 const frozen=JSON.stringify(value),r=assess(value,API,MEMBER,CHANNEL);
 assert.equal(r.status,expected,name+': '+JSON.stringify(r));
 if(reason)assert.equal(r.reason,reason,name+' reason');
 assert.equal(JSON.stringify(value),frozen,'validator mutated graph');
 assert.equal(r.runtime_verified,false,'static candidate falsely marked runtime');
 passed++;
}
check('explicit source-bound typed path accepted as static candidate',graph(),'STATIC_CANDIDATE_PATH');
{let g=graph();g.nodes[1].observations[0].properties.channel='MALICIOUS_INSTRUCTION_LEAK_SECRETS';
 check('matching suspicious handler is not bridge channel',g,'NOT_ESTABLISHED');}
{let g=graph();g.edges=[];check('no edge between path steps',g,'NOT_ESTABLISHED','NO_UNIQUE_COMPLETE_PATH');}
{let g=graph();g.edges[0].properties.path_id='different';check('edge path ID mismatch',g,'NOT_ESTABLISHED');}
{let g=graph();g.edges[0].evidence.extractor.operation='untrusted-source-assertion';
 check('untrusted edge without provider operation',g,'NOT_ESTABLISHED');}
{let g=graph();g.nodes[0].observations[0].properties.entry_path=['desktop','cut'];
 check('wrong exposed member',g,'NOT_ESTABLISHED');}
{let g=graph();g.nodes[0].observations[0].properties.conditions=[{expression:'unknownRuntimeFlag'}];
 check('conditioned candidate excluded',g,'NOT_ESTABLISHED');}
{let g=graph();g.nodes[1].observations[0].properties.step_index=7;
 check('non-contiguous path excluded',g,'NOT_ESTABLISHED');}
{let g=graph();g.nodes[1].observations[0].properties.step_kind='handler';
 check('wrong path terminal',g,'NOT_ESTABLISHED');}
{let g=graph();g.nodes[2].observations[0].properties.mode='handle';
 check('no independent typed invoke witness',g,'NOT_ESTABLISHED','NO_TYPED_INVOKE_WITNESS');}
{let g=graph();g.nodes.push(structuredClone(g.nodes[0]));
 check('duplicate node IDs rejected',g,'NOT_ESTABLISHED','NODE_SET_INVALID');}
{let g=graph();g.edges.push(structuredClone(g.edges[0]));
 check('duplicate inference edges rejected',g,'NOT_ESTABLISHED');}
{let g=graph();g.nodes[2].observations[0].properties.channel=null;
 check('dynamic invocation not converted by handler',g,'NOT_ESTABLISHED','NO_TYPED_INVOKE_WITNESS');}
{let g=graph();g.nodes[0].observations[0].properties.entry_path=['desktop','copy','nested'];
 g.nodes[1].observations[0].properties.entry_path=['desktop','copy','nested'];
 check('non-exact member path excluded',g,'NOT_ESTABLISHED');}
{let g=graph();g.edges[0].relation='handles';check('handler edge is not call path',g,'NOT_ESTABLISHED');}
{let g=graph();g.nodes[0].observations[0].properties.resolution='dynamic';
 check('dynamic model-supplied path resolution excluded',g,'NOT_ESTABLISHED');}
{let g=graph();g.nodes[2].observations[0].properties.channel='other';
 check('literal mismatch rejected even same API',g,'NOT_ESTABLISHED');}
{let g=graph();g.edges.push({source_node_id:'exp',target_node_id:'handler-decoy',relation:'handles',properties:{path_id:'pathA'}});
 check('extra unrelated handler edge does not become a path',g,'STATIC_CANDIDATE_PATH');}
{let g=graph();g.nodes.push({node_id:'other-exp',kind:'javascript-expression',
 observations:[{properties:{path_id:'pathB',entry_kind:'bridge-member',entry_path:['desktop','copy'],
  step_kind:'exposure',step_index:0,channel:CHANNEL,conditions:[],resolution:'candidate'}}]});
 g.nodes.push({node_id:'other-terminal',kind:'javascript-expression',
 observations:[{properties:{path_id:'pathB',entry_kind:'bridge-member',entry_path:['desktop','copy'],
  step_kind:'terminal',step_index:1,channel:CHANNEL,conditions:[],resolution:'candidate'}}]});
 g.edges.push({source_node_id:'other-exp',target_node_id:'other-terminal',relation:'calls',
  properties:{path_id:'pathB',resolution:'candidate'},evidence:{extractor:{operation:'trace-electron-wrapper-path'}}});
 check('ambiguous duplicate distinct candidate paths excluded',g,'NOT_ESTABLISHED','AMBIGUOUS_CANDIDATE_PATHS');}
check('malformed graph fails closed',{},'NOT_ESTABLISHED','GRAPH_OR_QUERY_INVALID');
console.log(JSON.stringify({schema:'P71_API_CHANNEL_CANDIDATE_UNIT_v0.1',
  passed,disposition:'PASS',qualification:'NOT_ESTABLISHED'}));
