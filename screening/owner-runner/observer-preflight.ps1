# PUBLIC SYNTHETIC OBSERVER: native Get-Process, not CIM/WMI.
# Observes PID+start identity and exit; cannot independently prove ancestry.
$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'PowerShell executable unavailable' }
$child = $null
try {
    $child = Start-Process -FilePath $exe -ArgumentList '-NoProfile -NonInteractive -Command "Start-Sleep -Seconds 30"' -PassThru -WindowStyle Hidden
    $observed = Get-Process -Id $child.Id -ErrorAction Stop
    if ($observed.Id -ne $child.Id) { throw 'Get-Process reported a different PID' }
    $created = $observed.StartTime.ToUniversalTime().ToString('o')
    if ([string]::IsNullOrWhiteSpace($created)) { throw 'Process start identity missing' }
    $child.Kill()
    if (-not $child.WaitForExit(15000)) { throw 'Synthetic child did not settle in 15 seconds' }
    $remaining = Get-Process -Id $child.Id -ErrorAction SilentlyContinue
    if ($null -ne $remaining) {
        $afterCreated = $remaining.StartTime.ToUniversalTime().ToString('o')
        if ($afterCreated -eq $created) { throw 'Process with same PID and start identity remains alive' }
    }
    [ordered]@{
        test = 'non-cim-pid-starttime-observation'
        status = 'PASS'
        source = 'Get-Process'
        pid_identity_observed = $true
        exited_identity_absent = $true
        parent_child_lineage = 'NOT_ESTABLISHED'
        scope = 'PUBLIC_SYNTHETIC_ONLY'
    } | ConvertTo-Json -Compress
}
finally {
    if ($null -ne $child) {
        try { if (-not $child.HasExited) { $child.Kill(); $child.WaitForExit(5000) | Out-Null } } catch { }
        $child.Dispose()
    }
}
