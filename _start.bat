@echo off
REM ---------------------------------------------------------------
REM  Har .bat isse pehle bulata hai.
REM
REM  Pehle bat files seedha "call .venv\Scripts\activate.bat" karti thin.
REM  .venv na ho to Windows chupchaap aage badh jata tha, system Python
REM  chal jata tha, aur error kuch aur hi aata tha:
REM      ModuleNotFoundError: No module named 'dotenv'
REM  Usse ye pata hi nahi chalta ki asli baat "setup.bat nahi chalaya" hai.
REM ---------------------------------------------------------------

if not exist "%~dp0.venv\Scripts\activate.bat" (
  echo.
  echo  ============================================================
  echo   Is folder me setup abhi nahi hua hai.
  echo.
  echo   %~dp0
  echo.
  echo   Pehle setup.bat chalao. Wo Python ka dabba banayega aur
  echo   saari libraries install karega. Ek hi baar karna hai.
  echo  ============================================================
  echo.
  exit /b 1
)

call "%~dp0.venv\Scripts\activate.bat"

python -c "import dotenv, playwright, yaml" >nul 2>&1
if errorlevel 1 (
  echo.
  echo  ============================================================
  echo   .venv to hai par libraries adhoori hain.
  echo   setup.bat dobara chalao -- wo bacha hua install kar dega.
  echo  ============================================================
  echo.
  exit /b 1
)
exit /b 0
