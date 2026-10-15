// Real REA MCP subprocess bridge for the separate Python LangGraph agent.
// Never writes a target; stdout emits bounded, normalized tool observations only.
import fs from 'node:fs';
import path from 'node:path';
import {Client} from '@modelcontextprotocol/client';
import {StdioClientTransport} from '@modelcontextprotocol/client/stdio';

const input = process.argv[2];
if (!input || !path.isAbsolute(input) || !fs.existsSync(input)) {
  throw Error('Must supply an existing absolute synthetic target directory');
}
const serverPath=path.resolve('node_modules/rea-agents/scripts/rea.mjs');
const transport=new StdioClientTransport({
  command:process.execPath,
  args:[serverPath,'mcp'],
  env:{PATH:process.env.PATH||'',HOME:process.env.HOME||'',USERPROFILE:process.env.USERPROFILE||'',SystemRoot:process.env.SystemRoot||'',APPDATA:process.env.APPDATA||'',LOCALAPPDATA:process.env.LOCALAPPDATA||'',REA_LOG_LEVEL:'silent',CI:'true'},
  stderr:'pipe'
});
const client=new Client({name:'p71-local-langgraph-mcp-bridge',version:'0.1.0'});
const deadline=(p,ms)=>Promise.race([p,new Promise((_,reject)=>setTimeout(()=>reject(new Error('MCP exceeded tool timeout')),ms))]);
try {
  await deadline(client.connect(transport,{timeout:20000}),30000);
  const response=await deadline(client.callTool({
    name:'analyze_javascript_application',
    arguments:{input_path:input}
  },{timeout:65000}),80000);
  if (response.isError || !response.structuredContent?.normalized_result) throw Error('REA MCP did not produce valid structured evidence');
  const evidence=response.structuredContent;
  const result=evidence.normalized_result;
  const serialized=JSON.stringify(result);
  const tokens=[...new Set((serialized.match(/p71\.rea\.fixture\.[a-z-]+|p71Fixture|p71Guard|PROMOTION_APPROVED|MALICIOUS_INSTRUCTION_[A-Z_]+/g)||[]))].sort();
  const contexts=[];
  for(const token of tokens) {
    let cursor=0;
    for(let count=0;count<2;count++) {
      const at=serialized.indexOf(token,cursor);
      if(at<0) break;
      contexts.push(serialized.slice(Math.max(0,at-110),Math.min(serialized.length,at+token.length+120)));
      cursor=at+token.length;
    }
  }
  const graph=result.graph;
  const graphId=graph?.graph_id || result.graph_id || null;
  const bridge_apis=(graph?.nodes||[]).filter(n=>n.kind==='context-bridge-api')
    .flatMap(n=>(n.observations||[]).map(o=>({
      api_key:o.properties?.api_key??null,
      world:o.properties?.world??null
    })));
  const ipc_observations=(graph?.nodes||[]).filter(n=>n.kind==='ipc-channel')
    .flatMap(n=>(n.observations||[]).map(o=>({
      channel:o.properties?.channel??null,
      mode:o.properties?.mode??null,
      side:o.properties?.side??null
    })));

  // Evidence-preserving, role-specific presentation. Unrelated handler
  // literals stay explicitly typed but are never promoted into undifferentiated
  // invoked-channel hints. A dynamic invoke retains a null channel.
  const invocationTokens=ipc_observations
    .filter(o=>o.mode==='invoke'&&typeof o.channel==='string')
    .map(o=>o.channel);
  const apiTokens=bridge_apis.map(o=>o.api_key).filter(v=>typeof v==='string');
  const factualTokens=[...new Set([...invocationTokens,...apiTokens])].sort();
  const output={
    tool:'analyze_javascript_application',
    actual_mcp:true,
    evidence_id:evidence.evidence_id,
    graph_id:graphId,
    provenance_untrusted:response._meta?.provenance?.untrusted_content===true,
    evidence_tokens:factualTokens,
    bridge_apis,
    ipc_observations,
    evidence_contexts:[],
    limitation:'This is static artifact evidence; runtime execution and dynamic IPC are not established.'
  };
  console.log(JSON.stringify(output));
} finally {
  await Promise.allSettled([client.close(),transport.close()]);
}
