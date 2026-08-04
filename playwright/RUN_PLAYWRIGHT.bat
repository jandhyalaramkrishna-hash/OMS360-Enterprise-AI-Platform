@echo off
setlocal
REM =============================================================
REM  OMS-360 - Playwright QA Automation Runner (Windows)
REM  Run this from inside the "playwright" folder, or double-click it
REM  from Windows Explorer - it changes to its own folder first.
REM
REM  Prerequisites (one-time):
REM    1. OMS-360 must be running:  START_OMS360.bat  (repo root)
REM       -> confirm http://localhost:8000/health returns HEALTHY
REM    2. Node.js 18+ installed
REM    3. From this "playwright" folder, run once:
REM         npm install
REM         npx playwright install --with-deps chromium
REM
REM  What this script does:
REM    1. Runs the full Playwright suite against http://localhost:8000
REM    2. Produces: playwright-report/ (HTML report)
REM                 test-results/       (screenshots on failure, videos on
REM                                      failure, traces on first retry,
REM                                      results.json)
REM    3. Opens the HTML report in your default browser when done.
REM
REM  Does NOT modify any application source code - it only exercises the
REM  running app over HTTP/HTTPS, exactly like a browser or Postman would.
REM =============================================================

cd /d "%~dp0"

echo.
echo [1/3] Checking OMS-360 is reachable at http://localhost:8000 ...
curl -s -o nul -w "  Health endpoint HTTP status: %%{http_code}\n" http://localhost:8000/health
if errorlevel 1 (
    echo.
    echo   [WARN] Could not reach http://localhost:8000/health.
    echo   Make sure START_OMS360.bat has finished and reports "Engine is responding".
    echo   Continuing anyway - tests will fail fast if the app is not up.
    echo.
)

if not exist node_modules (
    echo [2/3] node_modules not found - running npm install ...
    call npm install
    if errorlevel 1 (
        echo   [ERROR] npm install failed. See output above.
        pause
        exit /b 1
    )
) else (
    echo [2/3] Dependencies already installed - skipping npm install.
)

echo.
echo [3/3] Running the Playwright suite ...
call npx playwright test
set TEST_EXIT_CODE=%ERRORLEVEL%

echo.
echo =============================================================
echo  Run finished (exit code %TEST_EXIT_CODE%).
echo  HTML report : playwright-report\index.html
echo  Artifacts   : test-results\  (screenshots / videos / traces on failure)
echo  JSON results: test-results\results.json
echo =============================================================
echo.
echo Opening the HTML report ...
call npx playwright show-report

endlocal
exit /b %TEST_EXIT_CODE%
