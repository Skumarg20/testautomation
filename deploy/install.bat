@echo off
REM ======================================================================
REM  Test Studio for the QA team - first install on the server (run once).
REM  Run it from an Administrator command prompt for the firewall / service
REM  steps. Read ui_studio\DEPLOY.md for the details.
REM ======================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0.."
set PORT=%STUDIO_PORT%
if "%PORT%"=="" set PORT=8778

echo.
echo [1/7] Python 3.11 or newer ...
where python >nul 2>&1
if errorlevel 1 ( echo   Python is not installed: install Python 3.12 from python.org, then run this again. & pause & exit /b 1 )
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 ( echo   Python 3.11 or newer is needed. & pause & exit /b 1 )

echo [2/7] Studio libraries (the exact versions it was tested with) ...
if not exist .venv python -m venv .venv
.venv\Scripts\python -m pip install -q --upgrade pip
.venv\Scripts\python -m pip install -q -r deploy\requirements-lock.txt
if errorlevel 1 ( echo   Installing the libraries failed: check the internet / proxy and run this again. & pause & exit /b 1 )
.venv\Scripts\python -m playwright install chromium
if errorlevel 1 ( echo   Installing Chromium failed. & pause & exit /b 1 )

echo [3/7] Python scripts (e2e_scripts) ...
if exist e2e_scripts (
  if not exist e2e_scripts\.venv python -m venv e2e_scripts\.venv
  e2e_scripts\.venv\Scripts\python -m pip install -q -r deploy\requirements-e2e-lock.txt
  e2e_scripts\.venv\Scripts\python -m playwright install chromium
)

echo [4/7] First admin ...
.venv\Scripts\python -c "from ui_studio import accounts; import sys; sys.exit(0 if any(u['role']=='admin' for u in accounts.list_users()) else 1)" >nul 2>&1
if errorlevel 1 (
  set /p ADMIN_EMAIL=  E-mail of the first admin ^(their login^):
  .venv\Scripts\python -m ui_studio.accounts add !ADMIN_EMAIL! --admin --name "Admin"
) else (
  echo   An admin already exists.
)

echo [5/7] App under test (MargBooks URL, login, company) ...
if not exist config\environments.json (
  echo   Not set yet. After this script: run studio.bat once on this server, open Settings ^> App under test,
  echo   fill the MargBooks URL, login and company, tick "Allow tests that create or change data" if wanted, Save.
)

echo [6/7] Firewall: allow port %PORT% on this server (needs Administrator) ...
netsh advfirewall firewall show rule name="Test Studio" >nul 2>&1
if errorlevel 1 netsh advfirewall firewall add rule name="Test Studio" dir=in action=allow protocol=TCP localport=%PORT% >nul 2>&1
if errorlevel 1 ( echo   Could not add the firewall rule: run this as Administrator, or open port %PORT% by hand. )

echo [7/7] Windows service (keeps the Studio running after logoff and reboot) ...
where nssm >nul 2>&1
if errorlevel 1 (
  echo   NSSM not found. Download it from https://nssm.cc, put nssm.exe in PATH, then run deploy\service.bat.
  echo   Or start it by hand with studio-server.bat.
) else (
  call "%~dp0service.bat"
)

echo.
echo Pre-flight check:
set STUDIO_MODE=server
.venv\Scripts\python -m ui_studio.preflight
echo.
echo Done. Open http://^<this server^>:%PORT% in a browser and log in with the admin e-mail.
echo Add the QA team in Team ^> Users ^& access (each gets a "set your password" link).
pause
