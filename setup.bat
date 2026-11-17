@echo off
cd /d "%~dp0"
echo ================================================
echo   MargBooks QA Agent -- Setup (ek hi baar)
echo ================================================
echo.
where python >nul 2>&1
if errorlevel 1 (
  echo   Python nahi mila. python.org se install karo,
  echo   phir ye window band karke dobara chalao.
  pause & exit /b 1
)
if not exist .venv (
  echo [1/4] Python ka dabba bana rahe hain...
  python -m venv .venv
) else (
  echo [1/4] .venv pehle se hai
)
call .venv\Scripts\activate.bat
echo [2/4] Libraries install kar rahe hain... ^(3-5 min^)
python -m pip install -q --upgrade pip
pip install -q playwright pytest pytest-html pyyaml python-dotenv faker rich openpyxl
echo [3/4] Chrome download kar rahe hain... ^(2-3 min^)
python -m playwright install chromium
if not exist .env (
  echo [4/4] .env bana rahe hain -- ISME APNA LOGIN BHARNA HAI
  copy .env.example .env >nul
  notepad .env
) else (
  echo [4/4] .env pehle se hai
)
echo.
echo Jaanch kar rahe hain...
python -c "import dotenv, playwright, yaml, faker" >nul 2>&1
if errorlevel 1 (
  echo.
  echo   !! Libraries poori tarah install nahi huin.
  echo      Internet dekh lo aur setup.bat dobara chalao.
  pause & exit /b 1
)
echo.
echo ================================================
echo   SETUP DONE. Ab doctor.bat chalao.
echo ================================================
pause
