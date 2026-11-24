@echo off
REM  Update the team Test Studio to the newest code: backup, new code, libraries, tests, restart, check.
REM  Run as Administrator on the server. Nothing of the team's data is lost (database, test cases, settings
REM  stay; the database is upgraded by itself on the first start).
setlocal
cd /d "%~dp0.."
call "%~dp0..\_start.bat"
if errorlevel 1 ( pause & exit /b 1 )
set PORT=%STUDIO_PORT%
if "%PORT%"=="" set PORT=8778

echo [1/6] Backup first ...
.venv\Scripts\python deploy\backup.py
if errorlevel 1 ( echo   Backup failed: update stopped, nothing changed. & pause & exit /b 1 )

echo [2/6] New code ...
where git >nul 2>&1
if errorlevel 1 (
  echo   git not found: copy the new code into this folder by hand ^(keep config\, testcases\, locators\^), then press a key.
  pause
) else (
  git pull --ff-only
  if errorlevel 1 ( echo   git pull failed ^(local changes?^): fix it, then run this again. & pause & exit /b 1 )
)

echo [3/6] Libraries ...
.venv\Scripts\python -m pip install -q -r deploy\requirements-lock.txt
if exist e2e_scripts\.venv e2e_scripts\.venv\Scripts\python -m pip install -q -r deploy\requirements-e2e-lock.txt

echo [4/6] Unit tests (nothing goes live if they fail) ...
.venv\Scripts\python -m pytest tests\unit -q -p no:cacheprovider
if errorlevel 1 ( echo   Tests failed: the running Studio was NOT restarted. Roll back: git checkout the previous commit. & pause & exit /b 1 )

echo [5/6] Restart ...
where nssm >nul 2>&1
if errorlevel 1 ( echo   No NSSM service: stop the running studio-server.bat window and start it again, then press a key. & pause ) else ( nssm restart TestStudio )
timeout /t 8 >nul

echo [6/6] Check ...
set STUDIO_MODE=server
.venv\Scripts\python -m ui_studio.preflight
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:%PORT%/healthz -TimeoutSec 15).Content } catch { 'The Studio did not answer: see logs\service.err.log' }"
pause
