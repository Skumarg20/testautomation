@echo off
REM  Test Studio for the whole QA team (server mode): everybody opens it in the browser and logs in.
REM  Read ui_studio\DEPLOY.md first. The first admin is made once with:
REM      .venv\Scripts\python -m ui_studio.accounts add <username> --admin
cd /d "%~dp0"
call "%~dp0_start.bat"
if errorlevel 1 ( pause & exit /b 1 )
set STUDIO_MODE=server
if "%STUDIO_HOST%"=="" set STUDIO_HOST=0.0.0.0
if "%STUDIO_PORT%"=="" set STUDIO_PORT=8778
if "%STUDIO_MAX_BROWSERS%"=="" set STUDIO_MAX_BROWSERS=3
python -m ui_studio.server
pause
