#!/usr/bin/env python3
"""Off-host REA native PE reproducibility diagnostic, *not* an acceptance test.

Uses same original toolchain and byte-checked source. Does not change protected
source, REA owner behavior, MSI or Factory. Never upgrades C5 status.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

PIN="3b79af28e80785afce9f5998d8f03289402a1847"
BASE_SHA="62f42a40aa841aafec5b81df62200b5dc5ce3064037383a7d3cb0d26faa1063a"
COPY_SHA="78406a3c7e8380233a767b1f1e720288383b475a0e0a1a326524f2e60dffaa0b"

def digest(blob):
    return hashlib.sha256(blob).hexdigest()

def sections(blob):
    if blob[:2]!=b"MZ":raise RuntimeError("NOT_PE")
    pe=struct.unpack_from("<I",blob,0x3c)[0]
    if blob[pe:pe+4]!=bytes((80,69,0,0)):raise RuntimeError("NOT_PE_SIGNATURE")
    total=struct.unpack_from("<H",blob,pe+6)[0]
    optsize=struct.unpack_from("<H",blob,pe+20)[0]
    result={}
    for j in range(total):
        o=pe+24+optsize+j*40
        name=blob[o:o+8].split(bytes((0,)))[0].decode("ascii","replace")
        size,raw=struct.unpack_from("<II",blob,o+16)
        if raw+size>len(blob): raise RuntimeError("PE_SECTION_OUT_OF_BOUNDS")
        result[name]={"raw_offset":raw,"raw_bytes":size,"sha256":digest(blob[raw:raw+size])}
    return result

def diagnostic(original,copy):
    a=original.read_bytes();b=copy.read_bytes()
    diffs=[i for i in range(min(len(a),len(b))) if a[i]!=b[i]]
    sa=sections(a);sb=sections(b)
    keys=set(sa)|set(sb)
    return {"byte_identical":a==b,"original_sha256":digest(a),
            "copy_sha256":digest(b),"original_bytes":len(a),"copy_bytes":len(b),
            "byte_difference_count":len(diffs),
            "first_16_offsets":diffs[:16],
            "sections":{k:{"original_sha256":sa.get(k,{}).get("sha256"),
                           "copy_sha256":sb.get(k,{}).get("sha256"),
                           "byte_identical":sa.get(k,{}).get("sha256")==sb.get(k,{}).get("sha256")}
                        for k in sorted(keys)},
            "original_source_root_visible_utf8":b"original-upstream" in a,
            "copy_source_root_visible_utf8":b"screening/owner-isolation" in b}

def main():
    if len(sys.argv)!=6:
        raise SystemExit("usage: script ORIG_A COPY_A ORIG_B COPY_B OUTPUT_DIR")
    a,b,ar,br=map(Path,sys.argv[1:5]);output=Path(sys.argv[5]);output.mkdir(parents=True,exist_ok=True)
    first=diagnostic(a,b)
    second=diagnostic(ar,br)
    original_repeated=a.read_bytes()==ar.read_bytes()
    copy_repeated=b.read_bytes()==br.read_bytes()
    tools={}
    for label,left,right in (("strip_debug",a,b),("strip_all",a,b)):
        x=output/(label+"_original.node"); y=output/(label+"_copy.node")
        opts=["--strip-debug"] if label=="strip_debug" else ["--strip-all"]
        subprocess.run(["x86_64-w64-mingw32-objcopy",*opts,str(left),str(x)],check=True,timeout=30)
        subprocess.run(["x86_64-w64-mingw32-objcopy",*opts,str(right),str(y)],check=True,timeout=30)
        tools[label]=diagnostic(x,y)
        x.unlink();y.unlink()
    report={"schema":"rea.owner.native-byte-parity-diagnostic.v1",
            "source_commit":PIN,
            "scope":"SYNTHETIC_OFFHOST_BINARY_REPRODUCIBILITY_ONLY",
            "original_c5":"NOT_QUALIFIED",
            "copied_source_blobs":"BYTE_VERIFIED_AGAINST_PINNED_UPSTREAM",
            "original_prior_parity_failure_preserved":True,
            "prior_original_sha":BASE_SHA,
            "prior_copied_sha":COPY_SHA,
            "first_same_toolchain_build":first,
            "second_same_toolchain_build":second,
            "rebuild_original_same_root_stable":original_repeated,
            "rebuild_copy_same_root_stable":copy_repeated,
            "diagnostic_only_stripping":tools,
            "binary_equivalence_of_unmodified_artifacts":"PASS" if first["byte_identical"] else "FAIL",
            "source_component_qualification":"NOT_QUALIFIED",
            "next_rule":"Do not upgrade scope from a stripped/normalized comparison or CI lifecycle smoke tests."}
    path=output/"DIAGNOSTIC_RESULT.json";path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("REPRO_SUMMARY",json.dumps({
        "original_stable":original_repeated,"copy_stable":copy_repeated,
        "raw_equal":first["byte_identical"],"debug_stripped_equal":tools["strip_debug"]["byte_identical"],
        "all_stripped_equal":tools["strip_all"]["byte_identical"],
        "original_sha":first["original_sha256"],"copy_sha":first["copy_sha256"],
        "original_c5":"NOT_QUALIFIED"}))
    # This diagnostic exits successfully when honest results are recorded, even
    # when original binary equivalence remains a documented FAIL.

if __name__=="__main__":main()
