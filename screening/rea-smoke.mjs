/**
 * REA third-party bounded candidate screen (NOT a qualification receipt).
 * All target content is synthetic and created in the runner temp directory.
 * Does not register an agent or execute target program code.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';

const RELEASE = '6.5.0';
const reports = [];
const fixtureDir = fs.mkdtempSync(path.join(os.tmpdir(), 'rea-screen-'));
const installed = path.resolve('node_modules', 'rea-agents');
const executable = path.join(installed, 'scripts', 'rea.mjs');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const record = (gate, status, detail = '') => reports.push({ gate, status, detail });
const run = (args, timeoutMs = 90_000) => {
  const out = spawnSync(process.execPath, [executable, ...args], {
    encoding: 'utf8', maxBuffer: 15 * 1024 * 1024, timeout: timeoutMs,
    env: { ...process.env, NO_COLOR: '1', CI: 'true' }, windowsHide: true
  });
  return {
    status: out.status, error: out.error?.code || null,
    stdout: out.stdout || '', stderr: out.stderr || ''
  };
};
const parse = output => {
  try { return JSON.parse(output); } catch { return null; }
};
const treeDigest = root => {
  const items = [];
  function visit(dir, base = '') {
    for (const ent of fs.readdirSync(dir, { withFileTypes: true }).sort((a,b) => a.name.localeCompare(b.name))) {
      const rel = path.posix.join(base, ent.name);
      if (ent.isDirectory()) visit(path.join(dir, ent.name), rel);
      else if (ent.isFile()) items.push(rel + ':' + hash(fs.readFileSync(path.join(dir, ent.name))));
      else items.push(rel + ':UNSUPPORTED');
    }
  }
  visit(root);
  return hash(items.sort().join('\n'));
};
const graphId = evidence => {
  const visited = new Set();
  function visit(obj, depth = 0) {
    if (!obj || typeof obj !== 'object' || depth > 9 || visited.has(obj)) return null;
    visited.add(obj);
    if (obj.schema === 'JavaScriptApplicationGraph' && typeof obj.graph_id === 'string') return obj.graph_id;
    for (const val of Object.values(obj)) {
      const found = visit(val, depth + 1);
      if (found) return found;
    }
    return null;
  }
  return visit(evidence);
};
try {
  const pkg = JSON.parse(fs.readFileSync(path.join(installed, 'package.json'), 'utf8'));
  record('pinned-release', pkg.name === 'rea-agents' && pkg.version === RELEASE ? 'PASS' : 'FAIL',
    pkg.name + '@' + pkg.version);
  record('installed-cli-present', fs.existsSync(executable) ? 'PASS' : 'FAIL');
  const help = run(['--help'], 25_000);
  record('cli-startup', help.status === 0 && /rea|reverse/i.test(help.stdout) ? 'PASS' : 'FAIL',
    'exit=' + help.status + '; spawn_error=' + (help.error || 'none'));

  const app = path.join(fixtureDir, 'synthetic-app');
  fs.mkdirSync(app, { recursive: true });
  const files = {
    'package.json': JSON.stringify({ name: 'rea-screen-fixture', version: '1.0.0', private: true, main: 'main.cjs' },null,2),
    'main.cjs': "const {app, BrowserWindow, ipcMain} = require('electron');\nipcMain.handle('rea.screen.sum.v1', (_e,a,b)=>a+b);\napp.whenReady().then(()=>{const win=new BrowserWindow({webPreferences:{preload:require('node:path').join(__dirname,'preload.cjs')}});win.loadFile('index.html');});\n",
    'preload.cjs': "const {contextBridge, ipcRenderer} = require('electron');\ncontextBridge.exposeInMainWorld('reaScreen',{add:(a,b)=>ipcRenderer.invoke('rea.screen.sum.v1',a,b)});\n",
    'renderer.js': "window.reaScreen.add(2,3).then(x => { document.title='REA_SCREEN_EXPECTED_RESULT:'+x; });\n",
    'index.html': '<html><head></head><body><script src="renderer.js"></script></body></html>\n'
  };
  for (const [name, content] of Object.entries(files)) fs.writeFileSync(path.join(app, name), content);
  const sourceDigestBefore = treeDigest(app);
  const args = ['analyze-javascript-application', app, '--json'];
  const first = run(args);
  const firstJson = parse(first.stdout);
  const evidence = firstJson?.normalized_result ? firstJson : firstJson?.result;
  const identified = typeof evidence?.evidence_id === 'string' && Boolean(evidence?.normalized_result);
  const observedMarker = first.stdout.includes('rea.screen.sum.v1');
  record('synthetic-static-js', first.status === 0 && identified ? 'PASS' : 'FAIL',
    'exit=' + first.status + '; evidence=' + identified + '; spawn_error=' + (first.error || 'none'));
  record('expected-ipc-marker', first.status === 0 && observedMarker ? 'PASS' : 'FAIL',
    'IPC channel in output=' + observedMarker);
  const second = run(args);
  const secondJson = parse(second.stdout);
  const evidence2 = secondJson?.normalized_result ? secondJson : secondJson?.result;
  const g1 = graphId(evidence); const g2 = graphId(evidence2);
  record('repeatable-graph-identity', g1 && g2 ? (g1 === g2 ? 'PASS' : 'FAIL') : 'INCOMPLETE',
    g1 && g2 ? 'Two repeated static analyses produced comparable graph IDs' : 'Graph ID absent: inspect returned evidence before declaring repeatability');
  record('read-only-source-mutation', sourceDigestBefore === treeDigest(app) ? 'PASS' : 'FAIL',
    'Fixture file hashes unchanged');
  const missing = run(['analyze-javascript-application', path.join(fixtureDir, 'does-not-exist'), '--json'], 25_000);
  const parsedFailure = parse(missing.stdout);
  const explicitError = missing.status !== 0 && (Boolean(parsedFailure?.error) || /error|invalid|not found|ENOENT|missing/i.test(missing.stderr + missing.stdout));
  record('negative-missing-path', explicitError ? 'PASS' : 'FAIL',
    'exit=' + missing.status + '; spawn_error=' + (missing.error || 'none'));
  record('windows-ghidra-real-provider', 'NOT_TESTED', 'Ghidra and JDK are not installed by this candidate screen');
  record('agent-mcp-integration', 'NOT_TESTED', 'No agent registration or live MCP client configured');
} catch (e) {
  record('screen-execution', 'FAIL', e?.code || e?.name || 'unexpected exception');
} finally {
  try { fs.rmSync(fixtureDir, { recursive: true, force: true }); }
  catch { record('fixture-cleanup', 'FAIL', 'Temporary synthetic folder removal failed'); }
}
const gateFail = reports.some(r => r.status === 'FAIL');
const gateIncomplete = reports.some(r => r.status === 'INCOMPLETE');
const result = {
  schema: 'REA_SCREEN_v0.1.0',
  upstream_release: RELEASE,
  node: process.version, platform: process.platform, architecture: process.arch,
  qualification: 'NOT_QUALIFIED',
  disposition: gateFail ? 'SCREEN_FAIL' : gateIncomplete ? 'SCREEN_INCOMPLETE' : 'BOUNDED_SCREEN_PASS',
  tests: reports
};
console.log(JSON.stringify(result, null, 2));
process.exitCode = gateFail || gateIncomplete ? 1 : 0;
