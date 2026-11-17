@echo off
cd /d "%~dp0"
call "%~dp0_start.bat"
if errorlevel 1 ( pause & exit /b 1 )
pytest --tags smoke
pause
