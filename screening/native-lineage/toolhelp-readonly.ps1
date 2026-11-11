# Read-only Windows process snapshot for PROJ-0071 public synthetic lineage testing.
# This is not a process supervisor, launcher, REA adapter or qualification tool.
# Uses documented Toolhelp32 parent PID enumeration + Get-Process creation-time identity.
param([Parameter(Mandatory=$true)][string]$IdsCsv)
$ErrorActionPreference = 'Stop'
if ($IdsCsv -notmatch '^[1-9][0-9]*(,[1-9][0-9]*){0,8}$') {
  throw 'Invalid synthetic PID list'
}
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;

public static class P71ToolhelpSnapshot {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct PROCESSENTRY32W {
        public uint dwSize;
        public uint cntUsage;
        public uint th32ProcessID;
        public IntPtr th32DefaultHeapID;
        public uint th32ModuleID;
        public uint cntThreads;
        public uint th32ParentProcessID;
        public int pcPriClassBase;
        public uint dwFlags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=260)]
        public string szExeFile;
    }
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern IntPtr CreateToolhelp32Snapshot(uint flags, uint processId);
    [DllImport("kernel32.dll", EntryPoint="Process32FirstW", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool First(IntPtr snapshot, ref PROCESSENTRY32W entry);
    [DllImport("kernel32.dll", EntryPoint="Process32NextW", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool Next(IntPtr snapshot, ref PROCESSENTRY32W entry);
    [DllImport("kernel32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CloseHandle(IntPtr handle);

    public static Dictionary<uint,uint> ParentMap() {
        // TH32CS_SNAPPROCESS = 0x00000002. No process modifications.
        IntPtr handle = CreateToolhelp32Snapshot(0x2, 0);
        if (handle == new IntPtr(-1)) throw new Win32Exception(Marshal.GetLastWin32Error());
        try {
            var output = new Dictionary<uint,uint>();
            var e = new PROCESSENTRY32W();
            e.dwSize = (uint)Marshal.SizeOf<PROCESSENTRY32W>();
            if (!First(handle, ref e)) throw new Win32Exception(Marshal.GetLastWin32Error());
            do {
                output[e.th32ProcessID] = e.th32ParentProcessID;
                e.dwSize = (uint)Marshal.SizeOf<PROCESSENTRY32W>();
            } while (Next(handle, ref e));
            return output;
        } finally { CloseHandle(handle); }
    }
}
'@
function Read-Identity([int]$targetId) {
    try {
        $p = Get-Process -Id $targetId -ErrorAction Stop
        return $p.StartTime.ToUniversalTime().ToString('o')
    } catch {
        $reason = $_.FullyQualifiedErrorId
        if ($reason -like 'NoProcessFoundForGivenId*') { return $null }
        throw
    }
}
$ids = @($IdsCsv.Split(',') | ForEach-Object { [int]$_ })
$before = @{}
foreach ($targetId in $ids) { $before[$targetId] = Read-Identity $targetId }
$parents = [P71ToolhelpSnapshot]::ParentMap()
$after = @{}
foreach ($targetId in $ids) { $after[$targetId] = Read-Identity $targetId }
$observations = @()
foreach ($targetId in $ids) {
    $identityA = $before[$targetId]
    $identityB = $after[$targetId]
    if ($null -ne $identityA -and $null -ne $identityB -and $identityA -ne $identityB) {
        throw 'PID creation identity changed during process snapshot'
    }
    if ($null -eq $identityA -and $null -eq $identityB) {
        $observations += [pscustomobject]@{ pid=$targetId; found=$false; parent_pid=$null; start_utc=$null }
        continue
    }
    if ($null -eq $identityA -or $null -eq $identityB -or -not $parents.ContainsKey([uint32]$targetId)) {
        throw 'Process changed or was unobservable during snapshot'
    }
    $observations += [pscustomobject]@{
        pid=$targetId
        found=$true
        parent_pid=[int]$parents[[uint32]$targetId]
        start_utc=$identityA
    }
}
[pscustomobject]@{
    classification = 'PUBLIC_SYNTHETIC_READ_ONLY_OBSERVATION'
    observer = 'Toolhelp32 Process32FirstW/NextW + Get-Process StartTime'
    cim_wmi_used = $false
    observations = @($observations)
} | ConvertTo-Json -Compress -Depth 6
