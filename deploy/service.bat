@echo off
REM  Install / refresh the "TestStudio" Windows service with NSSM (https://nssm.cc). Run as Administrator.
REM  IMPORTANT: run the service as ONE fixed Windows account. Saved MargBooks passwords are encrypted for that
REM  account (Windows DPAPI); if it changes, every QA must enter their MargBooks password again.
setlocal EnableDelayedExpansion
cd /d "%~dp0.."
set PORT=%STUDIO_PORT%
if "%PORT%"=="" set PORT=8778
where nssm >nul 2>&1
if errorlevel 1 ( echo NSSM is not installed: https://nssm.cc & pause & exit /b 1 )

nssm status TestStudio >nul 2>&1
if errorlevel 1 nssm install TestStudio "%CD%\.venv\Scripts\python.exe" -m ui_studio.server
nssm set TestStudio AppDirectory "%CD%"
nssm set TestStudio AppEnvironmentExtra STUDIO_MODE=server STUDIO_HOST=0.0.0.0 STUDIO_PORT=%PORT% STUDIO_MAX_BROWSERS=3
nssm set TestStudio AppStdout "%CD%\logs\service.out.log"
nssm set TestStudio AppStderr "%CD%\logs\service.err.log"
nssm set TestStudio Start SERVICE_AUTO_START
if not exist logs mkdir logs

echo.
set /p SVC_USER=Windows account to run the service as (e.g. .\studio-svc), empty = keep the current one:
if not "!SVC_USER!"=="" (
  set /p SVC_PASS=Password of !SVC_USER!:
  nssm set TestStudio ObjectName "!SVC_USER!" "!SVC_PASS!"
)
nssm restart TestStudio
if errorlevel 1 nssm start TestStudio
timeout /t 8 >nul
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:%PORT%/healthz -TimeoutSec 15).Content } catch { 'The Studio did not answer: see logs\service.err.log' }"
pause
