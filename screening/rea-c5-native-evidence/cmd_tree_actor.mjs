// Cleared synthetic CMD transport through the unchanged original REA process owner
// plus its pre-existing test-only read-only evidence operation. NOT QHF acceptance.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { createInterface } from 'node:readline';

if (process.platform !== 'win32') throw new Error('WINDOWS_REQUIRED');
const [addon, commandScript, pythonExecutable, fixtureScript, markers] = process.argv.slice(2);
if (![addon, commandScript, pythonExecutable, fixtureScript, markers].every(Boolean))
  throw new Error('MISSING_SYNTHETIC_FIXTURE_ARGUMENT');
const native = createRequire(import.meta.url)(resolve(addon));
const quote = value => '"' + value.replace(/(\\*)"/gu, '$1$1\\"').replace(/(\\+)$/u, '$1$1') + '"';
const exe = process.env.ComSpec || process.env.COMSPEC || (process.env.SystemRoot + '\\System32\\cmd.exe');
const cmdline = quote(exe) + ' /D /C ' + quote(resolve(commandScript));
const env = ['SystemRoot', 'TEMP', 'TMP', 'PATH', 'COMSPEC']
  .filter(key => process.env[key]).map(key => key + '=' + process.env[key]);
env.push('REA_C5_PYTHON=' + resolve(pythonExecutable));
env.push('REA_C5_ROLE_SCRIPT=' + resolve(fixtureScript));
env.push('REA_C5_MARKERS=' + resolve(markers));
const launched = native.call('process_spawn', [exe, cmdline, resolve(markers), env]);
assert.equal(launched.jobAssigned, true);
assert.equal(launched.killOnOwnerClose, true);
let closed = false;
try {
  console.log('CMD_OWNER_READY ' + JSON.stringify({root_pid: launched.pid, source: 'REA_ORIGINAL_OWNER_CANDIDATE'}));
  const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
  const commands = input[Symbol.asyncIterator]();
  for (let i = 0; i < 2; ++i) {
    assert.equal((await commands.next()).value, 'observe');
    console.log('CMD_OWNER_SAMPLE ' +
      JSON.stringify(native.call('process_evidence', [launched.handle])));
  }
  assert.equal((await commands.next()).value, 'go');
  input.close();
  native.call('process_close', [launched.handle]);
  closed = true;
  console.log('CMD_OWNER_DONE ' + JSON.stringify({owner_closed: true}));
} finally {
  if (!closed) {
    try { native.call('process_terminate', [launched.handle]); } catch {}
    try { native.call('process_close', [launched.handle]); } catch {}
  }
}
