#!/usr/bin/env python3
"""Verify byte-exact MIT-licensed REA 6.5.0 native source isolation and binary parity.

No acceptance promotion: proves source identity and same-build native artifact parity.
"""
import hashlib, json, subprocess, sys
from pathlib import Path

PIN = "3b79af28e80785afce9f5998d8f03289402a1847"
BLOBS = {
  "native/windows/src/addon.cc": "bffd4cbd4e8c4fcab27646b36ea184407a6b0f1c",
  "native/windows/src/filesystem.cc": "e5129dbb7943048edc8b847dcee170a54216f4d1",
  "native/windows/src/process.cc": "55e4153455b732115812d12d17c94709c1a65fdb",
  "native/windows/src/authority.hpp": "c8bed30dcbc6f151f3f8d2650d4958723f7290a0",
  "scripts/build-windows-native.mjs": "e5eae6111544b52b22a30d4beabe6e416fb7a7eb",
  "LICENSE": "2d476d24fa5a9ae2ab35e5fd121494049eb2ee5d"
}
def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args]).decode().strip()
def sha(b):
    return hashlib.sha256(b).hexdigest()
def verify(upstream, isolated):
    if git(upstream,"rev-parse","HEAD") != PIN: raise RuntimeError("PINNED_COMMIT_MISMATCH")
    if git(upstream,"status","--porcelain"): raise RuntimeError("UPSTREAM_DIRTY")
    for path,expected in BLOBS.items():
        if git(upstream,"rev-parse","HEAD:"+path) != expected: raise RuntimeError("UPSTREAM_BLOB_DRIFT:"+path)
        orig=subprocess.check_output(["git","-C",str(upstream),"show","HEAD:"+path])
        copy=(isolated/path).read_bytes()
        if copy != orig: raise RuntimeError("VENDORED_BYTES_DIFFER:"+path)
        if sha(copy) != sha(orig): raise RuntimeError("VENDORED_DIGEST_DIFFER:"+path)
    package=json.loads((isolated/"package.json").read_text(encoding="utf-8"))
    if package.get("version") != "6.5.0" or package.get("private") is not True:
        raise RuntimeError("ISOLATED_PACKAGE_IDENTITY_MISMATCH")
def compare(upstream,isolated,out):
    verify(upstream,isolated)
    rel=Path("native/windows/build/rea-windows-x64.node")
    src=upstream/rel
    dst=isolated/rel
    if not src.is_file() or not dst.is_file():raise RuntimeError("BUILD_ARTIFACT_MISSING")
    if src.read_bytes()!=dst.read_bytes(): raise RuntimeError("STANDALONE_BINARY_DIFFERS_FROM_ORIGINAL")
    a=json.loads((upstream/"native/windows/build/manifest.json").read_text())
    b=json.loads((isolated/"native/windows/build/manifest.json").read_text())
    if a!=b or a.get("artifactSha256") != sha(src.read_bytes()) or a.get("packageVersion")!="6.5.0":
        raise RuntimeError("ORIGINAL_ISOLATED_MANIFEST_MISMATCH")
    r={"schema":"rea.owner.native-isolation.v1","source_commit":PIN,
       "vendor_original_git_blobs":BLOBS,"native_binary_sha256":sha(src.read_bytes()),
       "original_native_binary_bytes":len(src.read_bytes()),"isolated_build_binary_identical":True,
       "original_owner_source_modified":False,
       "original_c5":"NOT_QUALIFIED","original_qhf":"INDETERMINATE",
       "scope":"COPY_AND_SAME_TOOLCHAIN_BINARY_PARITY_ONLY"}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("INDEPENDENT_NATIVE_COPY_BYTE_IDENTICAL",r["native_binary_sha256"])
def record(upstream, isolated, directory):
    verify(upstream, isolated)
    directory.mkdir(parents=True,exist_ok=True)
    rel=Path("native/windows/build/rea-windows-x64.node")
    original=(upstream/rel).read_bytes()
    copied=(isolated/rel).read_bytes()
    om=json.loads((upstream/"native/windows/build/manifest.json").read_text())
    im=json.loads((isolated/"native/windows/build/manifest.json").read_text())
    if om.get("artifactSha256") != sha(original) or im.get("artifactSha256") != sha(copied):
        raise RuntimeError("INVALID_NATIVE_MANIFEST")
    if om.get("packageVersion") != im.get("packageVersion") or im.get("packageVersion")!="6.5.0":
        raise RuntimeError("WRONG_PACKAGE")
    exact=original==copied
    observation={"schema":"rea.owner.source-exact-separate-build.v1",
         "source_commit":PIN,"source_blob_match":"PASS","copied_source_gits":BLOBS,
         "original_artifact_sha256":sha(original),"copied_artifact_sha256":sha(copied),
         "binary_byte_equivalence_gate":"PASS" if exact else "FAIL",
         "binary_equivalence_NOT_assumed":not exact,
         "artifact_bytes":len(copied),"original_c5":"NOT_QUALIFIED",
         "component_qualification":"NOT_QUALIFIED",
         "scope":"EXACT_SOURCE_SEPARATE_BUILD_ONLY"}
    (directory/"isolation_receipt.json").write_text(json.dumps(observation,indent=2,sort_keys=True)+"\n")
    source_receipt={"schema":"rea.copied-original-native-source-receipt.v1",
         "source_commit":PIN,"source_dirty":False,"artifact_sha256":sha(copied),
         "original_blob_shas":BLOBS,"original_upstream_copied_byte_exactly":True,
         "separate_copy_binary_sha256":sha(copied),
         "original_binary_sha256":sha(original),
         "binary_byte_equivalence_gate":observation["binary_byte_equivalence_gate"],
         "original_c5":"NOT_QUALIFIED"}
    (directory/"source_receipt.json").write_text(json.dumps(source_receipt,indent=2,sort_keys=True)+"\n")
    print("SEPARATE_COPY_SOURCE_PASS_BINARY_PARITY_"+observation["binary_byte_equivalence_gate"],
          sha(original),sha(copied))

if __name__=="__main__":
    if len(sys.argv) not in (4,5):raise SystemExit("usage: isolation_verify.py verify|compare ORIGINAL ISOLATED [RECEIPT]")
    mode=sys.argv[1];u=Path(sys.argv[2]);i=Path(sys.argv[3])
    if mode=="verify" and len(sys.argv)==4: verify(u,i);print("SIX_ORIGINAL_SOURCE_BLOBS_EXACT");sys.exit()
    if mode=="compare" and len(sys.argv)==5:compare(u,i,Path(sys.argv[4]));sys.exit()
    if mode=="record" and len(sys.argv)==5:record(u,i,Path(sys.argv[4]));sys.exit()
    raise RuntimeError("INVALID_MODE_OR_ARGUMENTS")
