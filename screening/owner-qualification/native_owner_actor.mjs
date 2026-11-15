// Synthetic-only driver of ORIGINAL, unmodified REA 6.5.0 native process owner.
// The harness owns these fixture processes; it is not a Factory launcher or PMVT product.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';

if (process.platform !== 'win32') throw new Error('WINDOWS_NATIVE_REQUIRED');
const [artifact, mode] = process.argv.slice(2);
if (!artifact || !['natural', 'terminate', 'close', 'crash', 'synthetic_deadline'].includes(mode))
  throw new Error('INVALID_FIXTURE_ARGUMENTS');
const native = createRequire(import.meta.url)(resolve(artifact));
const quote = value => '"' + value.replace(/(\\*)"/gu, '$1$1\\"').replace(/(\\+)$/u, '$1$1') + '"';
const lifetime = mode === 'natural' ? 1900 : 14000;
const leafCode = 'setTimeout(function(){process.exit(0)},' + lifetime + ')';
const middleCode =
  "const cp=require('node:child_process');" +
  'const leaf=cp.spawn(process.execPath,["-e",' + JSON.stringify(leafCode) +
  '],{stdio:"ignore",windowsHide:true});' +
  'if(!leaf.pid)process.exit(42);console.log("PMVT_LEAF="+leaf.pid);' +
  'setTimeout(function(){process.exit(0)},' + lifetime + ')';
const rootCode =
  "const cp=require('node:child_process');" +
  'const mid=cp.spawn(process.execPath,["-e",' + JSON.stringify(middleCode) +
  '],{stdio:["ignore","pipe","ignore"],windowsHide:true});' +
  'if(!mid.pid)process.exit(43);console.log("PMVT_MID="+mid.pid);' +
  'mid.stdout.on("data",function(d){process.stdout.write(d)});' +
  'setTimeout(function(){process.exit(0)},' + lifetime + ')';
const line = [process.execPath, '-e', rootCode].map(quote).join(' ');
const env = ['SystemRoot', 'TEMP', 'TMP', 'PATH', 'COMSPEC']
  .filter(k => process.env[k]).map(k => k + '=' + process.env[k]);
const launched = native.call('process_spawn', [process.execPath, line, tmpdir(), env]);
let closed = false;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
try {
  assert.equal(launched.jobAssigned, true);
  assert.equal(launched.killOnOwnerClose, true);
  let output = '', first = null, mid = 0, leaf = 0;
  for (let i = 0; i < 160; ++i) {
    first = native.call('process_poll', [launched.handle]);
    output += first.stdout.toString();
    const m = output.match(/PMVT_MID=(\d+)/u);
    const l = output.match(/PMVT_LEAF=(\d+)/u);
    if (m) mid = Number(m[1]);
    if (l) leaf = Number(l[1]);
    if (mid > 0 && leaf > 0 && first.activeProcesses >= 3) break;
    await pause(25);
  }
  if (!(mid > 0 && leaf > 0 && first.activeProcesses >= 3))
    throw new Error('NESTED_SYNTHETIC_DESCENDANTS_NOT_OBSERVED');
  console.log('OWNER_READY ' + JSON.stringify({
    mode, pids: [launched.pid, mid, leaf], owner_reported_active: first.activeProcesses,
    owner_reported_job_assigned: launched.jobAssigned,
    owner_reported_kill_on_close: launched.killOnOwnerClose
  }));
  const command = await new Promise(resolve => process.stdin.once('data', b => resolve(String(b).trim())));
  assert.equal(command, 'go');
  if (mode === 'crash') throw new Error('HARNESS_MUST_KILL_ITS_SYNTHETIC_OWNER');
  if (mode === 'terminate' || mode === 'synthetic_deadline') {
    assert.equal(native.call('process_terminate', [launched.handle]), true);
  }
  if (mode !== 'close') {
    let settled = false;
    for (let i = 0; i < 260; ++i) {
      const s = native.call('process_poll', [launched.handle]);
      if (s.exitCode !== null && s.activeProcesses === 0 && s.stdoutEnded && s.stderrEnded) {
        settled = true; break;
      }
      await pause(25);
    }
    if (!settled) throw new Error('ORIGINAL_OWNER_DID_NOT_SETTLE');
  } else {
    assert.ok(native.call('process_poll', [launched.handle]).activeProcesses >= 1);
  }
  native.call('process_close', [launched.handle]);
  closed = true;
  console.log('OWNER_DONE ' + JSON.stringify({mode, owner_returned: true}));
} finally {
  if (!closed) {
    try { native.call('process_terminate', [launched.handle]); } catch {}
    try { native.call('process_close', [launched.handle]); } catch {}
  }
}
