@echo off
setlocal EnableDelayedExpansion
title OMS360 Enterprise Platform - Clean Restart
cd /d "%~dp0"

echo ============================================================
echo        OMS360 Enterprise Platform - Clean Restart
echo ============================================================
echo.
echo   This does a full recreate of ONLY the OMS360 containers
echo   defined in this project's docker-compose.yml
echo   (oms360_mysql, oms360_zookeeper, oms360_kafka,
echo    oms360_core_engine, oms360_consumer).
echo.
echo   It does NOT touch any other Docker project or container on
echo   this machine, and it does NOT remove any volumes - your
echo   MySQL data is preserved.
echo.
echo   [PREVIOUS VERSION WARNING - FIXED]
echo   An earlier version of this script ran
echo     "docker stop $(docker ps -q)"  and  "docker network prune -f"
echo   which stopped and disrupted EVERY running Docker container and
echo   network on this machine, not just OMS360's - a real risk to any
echo   other project you had running. This version is scoped strictly
echo   to OMS360's own containers via "docker compose down" against
echo   this project's own compose file, which Compose guarantees only
echo   ever affects this project's resources.
echo ============================================================
echo.

REM --------------------------------------------------------------------------
REM 1. Docker Desktop check
REM --------------------------------------------------------------------------
echo [1/3] Checking Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Docker Desktop is not running or not installed.
    pause
    exit /b 1
)
echo   [OK] Docker Desktop is running.

REM --------------------------------------------------------------------------
REM 2. Tear down ONLY this project's containers/network (never volumes).
REM    `docker compose down` (no -v) removes containers + the project
REM    network but leaves named volumes - including oms360_mysql_data -
REM    completely untouched. This never touches any other Docker project.
REM --------------------------------------------------------------------------
echo [2/3] Removing OMS360's own containers and network (data volumes preserved)...
docker compose -f docker-compose.yml down --remove-orphans
if errorlevel 1 (
    echo   [WARN] docker compose down reported an error - continuing anyway.
)

REM --------------------------------------------------------------------------
REM 3. Start fresh via the standard, fully-verified startup script.
REM --------------------------------------------------------------------------
echo [3/3] Starting OMS360 fresh via START_OMS360.bat...
echo.
call START_OMS360.bat
set "RESULT=%ERRORLEVEL%"

if "%RESULT%"=="0" (
    echo.
    echo ============================================================
    echo OMS360 clean restart complete.
    echo Swagger : http://localhost:8000/docs
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo [FAIL] Clean restart failed - see logs\startup.log for details.
    echo ============================================================
)
pause
endlocal
exit /b %RESULT%
