@echo off
cd /d "%~dp0"

echo ==========================================================
echo    MARGBOOKS UI CRAWLER
echo ==========================================================
echo.

call "%~dp0_start.bat"
if errorlevel 1 (
  echo.
  echo   Setup poora nahi hai. Upar likha hai kya karna hai.
  pause
  exit /b 1
)

REM goto ko IF (...) block ke ANDAR nahi rakhte -- batch me wo tootne ki
REM jaani-mani wajah hai. Uski jagah ek variable me argument rakh lete hain.
set ARGS=
if /i "%~1"=="--enable"       set ARGS=--enable
if /i "%~1"=="--enable-known" set ARGS=--enable-known
if /i "%~1"=="--resume"       set ARGS=--resume

REM Waqt ki seema. Ek crawl 28 GHANTE chal chuka hai aur sirf 3 page
REM nikale -- app beech me mar gayi thi aur crawler koshish karta raha.
if not "%~2"=="" set ARGS=%ARGS% --minutes %~2

if "%ARGS%"=="--enable" echo   Pehle Control Room jayenge aur HAR wo setting ON
if "%ARGS%"=="--enable" echo   karenge jiske dropdown me "Yes" ka vikalp hai.
if "%ARGS%"=="--enable" echo   Phir menu -^> submenu -^> page crawl hoga.
if "%ARGS%"=="--enable" echo.
if "%ARGS%"=="--enable" echo   Purani haalat backup hogi.
if "%ARGS%"=="--enable" echo   Wapas karne ke liye: restore-settings.bat
if "%ARGS%"=="--enable-known" echo   Sirf 15 jaani-pehchani settings ON hongi.
if "%ARGS%"=="--resume" echo   Jahan ruka tha wahan se chala rahe hain...
if "%ARGS%"=="" echo   Naya crawl. Settings ko haath NAHI lagayega.
if "%ARGS%"=="" echo.
if "%ARGS%"=="" echo   Chhupe hue field bhi chahiye:
if "%ARGS%"=="" echo       run-margbooks-crawler.bat --enable
if "%ARGS%"=="" echo   Seema badalni ho (default 90 min):
if "%ARGS%"=="" echo       run-margbooks-crawler.bat --enable 150
if "%ARGS%"=="" echo   Beech me ruk jaye to:
if "%ARGS%"=="" echo       run-margbooks-crawler.bat --resume
echo.

python -m framework.run_crawler %ARGS%
set CODE=%ERRORLEVEL%

echo.
if "%CODE%"=="0" echo   SAB THEEK -- crawler-output\metadata.json me sab kuch hai.
if "%CODE%"=="1" echo   KUCH HISSE FAIL HUE -- crawler-output\crawl-summary.json dekho.
if "%CODE%"=="2" echo   CRAWL SHURU HI NAHI HO PAYA -- upar wajah likhi hai.
echo.
pause
