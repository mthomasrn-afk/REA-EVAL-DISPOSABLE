// PROJ-0071: public synthetic one-session Ghidra owner observation.
// Test-only consumer of the original REA 6.5.0 implementation, not a new launcher.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { access } from "node:fs/promises";
import { resolve, join } from "node:path";
import { pathToFileURL } from "node:url";

const root = resolve(process.cwd());
const source = (path) => import(pathToFileURL(join(root, path)).href);
const { resolveGhidraAnalysisProfile } = await source("dist/ghidra/GhidraAnalysisProfile.js");
const { GhidraClient } = await source("dist/ghidra/GhidraClient.js");
const { inspectGhidraInstallation } = await source("dist/ghidra/GhidraInstallation.js");
const { SUPPORTED_GHIDRA_VERSION } = await source("dist/ghidra/GhidraInstallationPolicy.js");
const { GhidraHeadlessLauncher } = await source("dist/ghidra/GhidraLauncher.js");
const { GHIDRA_PROVIDER_IDENTITY } = await source("dist/ghidra/GhidraProviderCapabilities.js");
const { parseBinaryTarget } = await source("dist/application/BinaryTargetResolver.js");

assert.equal(process.platform, "win32");
assert.equal(process.arch, "x64");
assert.equal(SUPPORTED_GHIDRA_VERSION, "12.1.4");
assert.ok(process.env.GHIDRA_INSTALL_DIR, "Pinned Ghidra distribution unavailable");
assert.ok(process.env.JAVA_HOME, "Required JDK unavailable");

const installation = inspectGhidraInstallation({
  environment: process.env,
  installDir: process.env.GHIDRA_INSTALL_DIR,
  javaHome: process.env.JAVA_HOME,
});
assert.equal(installation.status, "available", "Original Ghidra installation check failed");
assert.equal(installation.providerVersion, "12.1.4");
assert.ok(installation.analyzeHeadlessPath);

const targetPath = join(root, "build", "fixtures", "rea-ghidra-windows.exe");
const parsed = await parseBinaryTarget(targetPath);
if (!parsed.ok) throw parsed.error;
const target = parsed.value;
assert.equal(target.format, "pe");
assert.equal(target.architecture, "x86_64");
assert.equal(target.managed, false);
const profile = await resolveGhidraAnalysisProfile(
  target, GHIDRA_PROVIDER_IDENTITY, installation,
);
if (!profile.ok) throw profile.error;
assert.ok(profile.value.profile);

const client = new GhidraClient({
  platform: installation.platform,
  launcher: new GhidraHeadlessLauncher({
    environment: process.env,
    analyzeHeadlessPath: installation.analyzeHeadlessPath,
    javaHome: process.env.JAVA_HOME,
    bridgeScriptPath: join(root, "bridge", "ghidra", "ReaGhidraBridge.java"),
    platform: "win32",
  }),
  targetPath: target.path,
  targetSha256: target.sha256,
  transport: "authenticated-loopback-tcp",
  providerVersion: SUPPORTED_GHIDRA_VERSION,
  profileDigest: profile.value.profile.digest,
});

function nonCimSnapshot(pid) {
  assert.ok(Number.isSafeInteger(pid) && pid > 0);
  const ps = '$p=Get-Process -Id ' + String(pid) +
    ' -ErrorAction SilentlyContinue; if ($null -eq $p) {' +
    ' [pscustomobject]@{found=$false} | ConvertTo-Json -Compress' +
    ' } else { [pscustomobject]@{found=$true;pid=$p.Id;' +
    ' start_utc=$p.StartTime.ToUniversalTime().ToString("o")}' +
    ' | ConvertTo-Json -Compress }';
  return JSON.parse(execFileSync("powershell.exe",
    ["-NoProfile", "-NonInteractive", "-Command", ps],
    {encoding:"utf8", timeout:20000, maxBuffer:4096}).trim());
}
async function exists(path) {
  try { await access(path); return true; } catch { return false; }
}

let coords, before, failure = null, started = false, closed = false;
try {
  const result = await client.start();
  if (!result.ok) throw result.error;
  started = true;
  assert.equal(result.value.provider.id, "ghidra");
  assert.equal(result.value.read_only, true);
  assert.equal(result.value.analysis_complete, true);
  coords = client.diagnostics();
  assert.equal(coords.transport, "authenticated-loopback-tcp");
  assert.equal(coords.target_sha256, target.sha256);
  assert.ok(typeof coords.process_id === "number");
  before = nonCimSnapshot(coords.process_id);
  assert.equal(before.found, true, "Get-Process could not observe original launcher PID");
  assert.equal(before.pid, coords.process_id);
  assert.ok(typeof before.start_utc === "string" && before.start_utc.length > 0);
} catch (error) { failure = error; }
finally {
  const outcome = await client.close().catch((error) => ({ok:false,error}));
  if (!outcome.ok) failure = new AggregateError(
    [failure, outcome.error].filter(Boolean), "Original Ghidra cleanup or start failed"
  );
  else closed = true;
}
if (failure) throw new Error("One Ghidra lifecycle failed: " +
  (failure instanceof AggregateError ? "cleanup_or_start_failure" : failure.name));
assert.ok(started && closed);
const after = nonCimSnapshot(coords.process_id);
assert.ok(!after.found || after.start_utc !== before.start_utc,
  "Original launcher process identity still active after close");
for (const name of ["runtime_root", "endpoint_path", "project_root"]) {
  if (typeof coords[name] === "string") {
    assert.equal(await exists(coords[name]), false, "Original runtime path persisted: " + name);
  }
}
console.log(JSON.stringify({
  classification: "PUBLIC_SYNTHETIC_GITHUB_RUNNER_NOT_FACTORY_QUALIFICATION",
  status: "PASS",
  original_owner: "GhidraHeadlessLauncher/spawnOwnedProviderProcess/WindowsOwnedProcess",
  ghidra_version: "12.1.4",
  fixture_sha256: target.sha256,
  session_read_only: true,
  original_start_and_close: true,
  independent_observer: "Get-Process PID+StartTime, no CIM",
  original_launcher_seen: true,
  identical_process_identity_absent_after_close: true,
  original_runtime_removed: true,
  independent_parent_lineage: "NOT_ESTABLISHED",
  non_elevated_msi_behavior: "NOT_TESTED",
  full_factory_qualification: "NOT_ESTABLISHED"
}));
