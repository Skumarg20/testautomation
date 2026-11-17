@echo off
cd /d "%~dp0"
call "%~dp0_start.bat"
if errorlevel 1 ( pause & exit /b 1 )
echo.
echo  Crawl ke liye badli hui Control Room settings wapas ki jayengi.
echo.
python -m framework.restore_settings
pause
