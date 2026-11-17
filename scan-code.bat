@echo off
cd /d "%~dp0"
call "%~dp0_start.bat"
if errorlevel 1 ( pause & exit /b 1 )
echo.
echo  MargBooks ke SOURCE CODE ka folder chahiye.
echo  (jisme src\ ya app\ folder ho -- node_modules apne aap chhod diya jayega)
echo.
set /p SRC="Folder ka poora path: "
python -m framework.scan_code "%SRC%"
pause
