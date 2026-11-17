@echo off
REM  Test Studio -- the new no-code UI (record or write a test, verify, replay, save).
REM  The old UI (ui.bat, port 8777) still works; both share the same tests and settings.
cd /d "%~dp0"
call "%~dp0_start.bat"
if errorlevel 1 ( pause & exit /b 1 )
python -m ui_studio.server
pause
