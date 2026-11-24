@echo off
REM  Daily backup of the team's data (users, run history, test cases, settings) to backups\<date>.
REM  Schedule it: schtasks /create /tn "Test Studio backup" /sc daily /st 21:00 /tr "%~dp0backup.bat"
REM  Copy the backups folder to another disk or share now and then.
cd /d "%~dp0.."
call "%~dp0..\_start.bat"
if errorlevel 1 exit /b 1
.venv\Scripts\python deploy\backup.py %1
