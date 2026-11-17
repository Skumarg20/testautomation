@echo off
cd /d "%~dp0"
call "%~dp0_start.bat"
if errorlevel 1 ( pause & exit /b 1 )
set /p SCR="Kaunsa screen dump karna hai (jaise sale_bill): "
python -m framework.dump --screen %SCR%
pause
