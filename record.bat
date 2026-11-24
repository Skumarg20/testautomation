@echo off
REM  Record a test on YOUR PC for the team Test Studio (the server cannot show you its browser window).
REM  Needs this folder set up once on your PC (setup.bat).
REM  Usage:  record.bat <MargBooks URL>   - use the URL shown on the Studio's Record screen (the environment the
REM  team Studio tests). Without it, this asks for the URL: it never guesses one, so a test is not recorded on the
REM  wrong MargBooks.
REM  A Chrome window and the Playwright Inspector open. Test the screen by hand, then copy ALL the code from the
REM  Inspector and paste it in Test Studio > Record > "Recorded code" > Use this code.
cd /d "%~dp0"
call "%~dp0_start.bat"
if errorlevel 1 ( pause & exit /b 1 )
set "URL=%~1"
if "%URL%"=="" (
  echo.
  echo  Which MargBooks should the recording open?
  echo  Copy the address from Test Studio ^> Record ^(the line "On your PC run: ..."^), for example
  echo  https://books6.margbooks.com
  echo.
  set /p "URL=MargBooks URL: "
)
if "%URL%"=="" (
  echo  No URL given. Run: record.bat ^<MargBooks URL from the Studio's Record screen^>
  pause
  exit /b 1
)
python -m playwright codegen --target=playwright-test "%URL%"
