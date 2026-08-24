@echo off
REM =============================================================================
REM OMS-360 Enterprise QA - newman.cmd runner
REM Runs the Postman collection against the local stack and produces CLI,
REM JSON, HTML Extra, and JUnit XML reports in postman\reports\, plus raw
REM Allure results merged into the repo-root allure-results\ directory
REM (combined there with pytest's own results by Generate_Allure_Report.bat /
REM Run_QA_Pipeline.bat into one unified Enterprise Allure report).
REM
REM This script NEVER installs software - see Setup_QA_Environment.bat for
REM one-time tooling setup (Newman, newman-reporter-htmlextra,
REM newman-reporter-allure).
REM
REM Prerequisite (every run): the stack must be up and healthy.
REM   START_OMS360.bat  (or) docker compose up -d
REM   curl http://localhost:8000/health
REM =============================================================================
setlocal
cd /d "%~dp0"

set COLLECTION=collection\OMS360.postman_collection.json
set ENVIRONMENT=environment\OMS360.postman_environment.json
set REPORT_DIR=reports
set ALLURE_RESULTS_DIR=..\allure-results

if not exist "%REPORT_DIR%" mkdir "%REPORT_DIR%"
if not exist "%ALLURE_RESULTS_DIR%" mkdir "%ALLURE_RESULTS_DIR%"

where newman >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Newman is not installed or not on PATH.
    echo         Run Setup_QA_Environment.bat first ^(one-time^).
    exit /b 1
)

echo =============================================================================
echo  OMS-360 newman.cmd run
echo =============================================================================

REM Tee CLI output to both the console and a persisted CLI report file via
REM PowerShell (bundled with Windows), while still propagating Newman's real
REM exit code back to this batch script through $LASTEXITCODE.
REM
REM IMPORTANT: --reporters' value is single-quoted below ('cli,json,htmlextra,
REM junit,allure'). PowerShell treats an UNQUOTED comma as its array-literal
REM operator - `cli,json,htmlextra,junit,allure` without quotes gets built
REM into a PowerShell array, then re-stringified with SPACES (not commas)
REM when handed to the native newman.exe process, corrupting the value into
REM one bogus reporter name ("could not find 'cli json htmlextra junit
REM allure' reporter"). Quoting it as one literal string avoids that.
REM
REM $PSNativeCommandUseErrorActionPreference = $false (PowerShell 7.3+) stops
REM PowerShell from re-wrapping ordinary native-command stderr chatter as
REM red NativeCommandError-formatted blocks - harmless to set on older
REM PowerShell versions too (it's just an inert variable there).
powershell -NoProfile -Command ^
    "$PSNativeCommandUseErrorActionPreference = $false; newman.cmd run '%COLLECTION%' -e '%ENVIRONMENT%' --reporters 'cli,json,htmlextra,junit,allure' --reporter-json-export '%REPORT_DIR%\newman-json-report.json' --reporter-htmlextra-export '%REPORT_DIR%\newman-html-report.html' --reporter-htmlextra-title 'OMS-360 Enterprise QA Report' --reporter-htmlextra-darkTheme --reporter-junit-export '%REPORT_DIR%\newman-junit-report.xml' --reporter-allure-resultsDir '%ALLURE_RESULTS_DIR%' --color off 2>&1 | Tee-Object -FilePath '%REPORT_DIR%\newman-cli-report.txt'; exit $LASTEXITCODE"

set NEWMAN_EXIT=%ERRORLEVEL%

echo.
echo =============================================================================
if %NEWMAN_EXIT% EQU 0 (
    echo  RESULT: ALL NEWMAN TESTS PASSED
) else (
    echo  RESULT: ONE OR MORE NEWMAN TESTS FAILED  ^(exit code %NEWMAN_EXIT%^)
)
echo  CLI report   : %REPORT_DIR%\newman-cli-report.txt
echo  JSON report  : %REPORT_DIR%\newman-json-report.json
echo  HTML report  : %REPORT_DIR%\newman-html-report.html
echo  JUnit report : %REPORT_DIR%\newman-junit-report.xml
echo  Allure raw   : %ALLURE_RESULTS_DIR%\  ^(merged with pytest results later^)
echo =============================================================================

endlocal & exit /b %NEWMAN_EXIT%
