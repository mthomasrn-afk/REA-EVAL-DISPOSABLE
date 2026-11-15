@echo off
setlocal
rem BOUNDED REA ORIGINAL OWNER CONFORMANCE, NOT FULL REA ACCEPTANCE.
rem This source-only candidate must not be run on MSI until qualified and admitted.
set "ROOT=%~dp0"
rem Reject staged CI candidate before ANY native execution.
if not exist "%ROOT%PACKAGE_STATUS.json" (
  echo BLOCKED: Acceptance package has no admission record.
  exit /b 23
)
powershell -NoProfile -NonInteractive -Command "$p=Get-Content -LiteralPath '%ROOT%PACKAGE_STATUS.json' -Raw | ConvertFrom-Json; if($p.status -ne 'ADMITTED_NATIVE_ACCEPTANCE') { exit 23 }"
if errorlevel 1 (
  echo BLOCKED: This candidate is not admitted for MSI execution.
  exit /b 23
)
if not defined REA_CLEANROOM_OUTPUT set "REA_CLEANROOM_OUTPUT=C:\SOFTWARE_FACTORY\REA Cleanroom\Output"
if not exist "%REA_CLEANROOM_OUTPUT%\" (
  echo BLOCKED: Original REA cleanroom Output directory was not found.
  exit /b 20
)
where python >nul 2>nul
if errorlevel 1 (
  echo BLOCKED: Existing Python executable not found. No installation attempted.
  exit /b 21
)
where node >nul 2>nul
if errorlevel 1 (
  echo BLOCKED: Existing Node executable not found. No installation attempted.
  exit /b 22
)
python -B "%ROOT%owner_host_acceptance.py" --addon "%ROOT%rea-windows-x64.node" --manifest "%ROOT%manifest.json" --source-receipt "%ROOT%source_receipt.json" --output-root "%REA_CLEANROOM_OUTPUT%" --host-label msi
exit /b %ERRORLEVEL%
