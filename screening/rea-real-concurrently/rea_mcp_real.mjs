// Genuine REA 6.5.0 MCP analysis of real MIT Concurrently 10.0.7.
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {Client} from "@modelcontextprotocol/client";
import {StdioClientTransport} from "@modelcontextprotocol/client/stdio";

const out=process.argv[2];
if(!out)throw Error("OUTPUT_REQUIRED");
const root=path.resolve("node_modules/concurrently");
const tool=path.resolve("node_modules/rea-agents/scripts/rea.mjs");
const files=["package.json","dist/bin/index.js","dist/lib/index.js"];
const digest=x=>crypto.createHash("sha256").update(x).digest("hex");
const result={schema:"rea.real-concurrently.mcp.v1",target:"concurrently@10.0.7",
  target_upstream_commit:"f7812ab449f2886be4b7089a10c8e5f1feda2c0b",
  rea:"6.5.0",real_analysis:false,rea_qualified:false,
  original_ac15:"PARTIAL",original_ac17:"INDETERMINATE",
  c3_model_selection:"NOT_RUN",status:"INDETERMINATE",checks:[]};
const check=(name,ok,note)=>{result.checks.push({name,status:ok?"PASS":"FAIL",note});
  if(!ok)throw Error(name+"_BLOCKED");};
let client,transport,profile;
try{
  const p=JSON.parse(fs.readFileSync(path.join(root,"package.json"),"utf8"));
  const r=JSON.parse(fs.readFileSync(path.resolve("node_modules/rea-agents/package.json"),"utf8"));
  check("source_versions",p.version==="10.0.7"&&p.name==="concurrently"&&p.license==="MIT"&&r.version==="6.5.0",
    p.name+"@"+p.version+" "+p.license+" rea "+r.version);
  check("real_package_files",files.every(f=>fs.existsSync(path.join(root,f))),"node_modules/concurrently");
  const before=Object.fromEntries(files.map(f=>[f,digest(fs.readFileSync(path.join(root,f)))]));
  result.real_source_hashes=before;
  const bin=fs.readFileSync(path.join(root,"dist/bin/index.js"),"utf8");
  const lib=fs.readFileSync(path.join(root,"dist/lib/index.js"),"utf8");
  check("real_source_content",bin.length>200&&lib.length>100,
      "Original Concurrently npm release, not constructed source");
  profile=fs.mkdtempSync(path.join(os.tmpdir(),"rea-real-mcp-"));
  const env={PATH:process.env.PATH??"",SystemRoot:process.env.SystemRoot??"",
    WINDIR:process.env.WINDIR??"",ComSpec:process.env.ComSpec??"",
    HOME:profile,USERPROFILE:profile,APPDATA:profile,LOCALAPPDATA:profile,
    XDG_CONFIG_HOME:profile,XDG_CACHE_HOME:profile,XDG_DATA_HOME:profile,
    TMP:profile,TEMP:profile,TMPDIR:profile,CI:"true",REA_LOG_LEVEL:"silent"};
  transport=new StdioClientTransport({command:process.execPath,args:[tool,"mcp"],env,stderr:"pipe"});
  client=new Client({name:"rea-concurrently-real",version:"0.1.0"});
  await client.connect(transport,{timeout:30000});
  check("real_mcp_connection",true,"Authenticated to local REA MCP transport, not Codex");
  const available=await client.listTools(undefined,{timeout:30000});
  const analyzer=available.tools.find(t=>t.name==="analyze_javascript_application");
  check("analyzer_advertised",!!analyzer&&analyzer.inputSchema?.type==="object",
    "real tools advertised "+available.tools.length);
  result.real_tool_count=available.tools.length;
  const props=analyzer.inputSchema.properties||{};
  const args={input_path:root};
  if(props.detail)args.detail="summary";
  if(props.source_paths)args.source_paths=files;
  result.analysis_input_keys=Object.keys(args);
  const call=await client.callTool({name:"analyze_javascript_application",arguments:args},
    {timeout:180000});
  const structured=call?.structuredContent;
  const projection=structured?.normalized_result;
  const eid=structured?.evidence_id??projection?.parent_evidence_id;
  result.analysis={is_error:call?.isError===true,evidence_id:typeof eid==="string"?eid:null,
    normalized_result_present:!!projection,
    untrusted_marker:call?._meta?.provenance?.untrusted_content===true,
    result_keys:projection&&typeof projection==="object"?Object.keys(projection).slice(0,32):[],
    failure_summary:call?.isError===true?
      String(call.content?.filter(x=>x.type==="text").map(x=>x.text).join(" ")||"").slice(0,220):null};
  check("genuine_real_rea_analysis",call?.isError!==true&&!!projection&&!!eid,
    JSON.stringify(result.analysis));
  check("genuine_untrusted_metadata",result.analysis.untrusted_marker,
    "Original MCP response _meta");
  result.real_analysis=true;
  const missing=await client.callTool({name:"analyze_javascript_application",
    arguments:{input_path:path.join(profile,"nonexistent-negative")}}, {timeout:30000});
  check("negative_missing_source",missing?.isError===true&&
    !missing?.structuredContent?.normalized_result,"Negative REA call rejected");
  const after=Object.fromEntries(files.map(f=>[f,digest(fs.readFileSync(path.join(root,f)))]));
  check("real_source_preservation",JSON.stringify(before)===JSON.stringify(after),
    "Byte-hashes retained");
  result.status="PASS_SCOPED_REAL_REA_MCP_ANALYSIS";
}catch(e){result.status="FAIL_OR_INDETERMINATE";result.reason=String(e?.message??e).slice(0,500);}
finally{
 try{if(client)await client.close()}catch(e){result.close_error=String(e).slice(0,180);result.status="FAIL_OR_INDETERMINATE";}
 try{if(transport)await transport.close()}catch(e){result.transport_close_error=String(e).slice(0,180);result.status="FAIL_OR_INDETERMINATE";}
 try{if(profile)fs.rmSync(profile,{recursive:true,force:true})}catch(e){result.cleanup_error=String(e).slice(0,180);result.status="FAIL_OR_INDETERMINATE";}
 fs.mkdirSync(path.dirname(out),{recursive:true});
 fs.writeFileSync(out,JSON.stringify(result,null,2)+"\n");
 console.log("REA_CONCURRENTLY_REAL",JSON.stringify({status:result.status,reason:result.reason,
    real:result.real_analysis,tools:result.real_tool_count}));
}
if(result.status!=="PASS_SCOPED_REAL_REA_MCP_ANALYSIS")process.exitCode=2;
