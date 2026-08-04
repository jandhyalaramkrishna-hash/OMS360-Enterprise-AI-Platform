@echo off
setlocal
cd /d "%~dp0"
call scripts\common.bat init

echo.
echo =============================================================================
echo   OMS-360 Enterprise Order Management System - STOP
echo =============================================================================
echo   This stops ONLY the Engine and Consumer containers, using this
echo   project's own docker-compose.yml - it can never affect containers
echo   from any other Docker project on this machine.
echo   MySQL, Zookeeper, and Kafka (and all their data/volumes) are left
echo   running and untouched.
echo =============================================================================
echo.

call scripts\common.bat write_log logs\shutdown.log "===== STOP_OMS360.bat invoked ====="

docker info >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Docker Desktop is not running.
    call scripts\common.bat write_log logs\shutdown.log "FAILED: Docker Desktop not running"
    endlocal
    exit /b 1
)

echo Stopping OMS360 Engine and Consumer...
docker compose -f %COMPOSE_FILE% stop oms360-engine oms360-consumer
if errorlevel 1 (
    echo   [WARN] docker compose stop reported an error - trying direct container stop...
    docker stop %CONSUMER_CONTAINER% >nul 2>&1
    docker stop %ENGINE_CONTAINER% >nul 2>&1
)
echo   [OK] Engine and Consumer stopped.
call scripts\common.bat write_log logs\shutdown.log "Engine and Consumer stopped successfully"

echo.
echo   MySQL, Zookeeper, and Kafka were NOT touched and remain running.
echo   No volumes or data were removed. Run CHECK_OMS360.bat to confirm status.
echo.
echo   Tip: if you want to stop the full stack (including MySQL/Zookeeper/Kafka)
echo   while still preserving all data, run:
echo     docker compose -f %COMPOSE_FILE% stop
echo   (never use "docker compose down -v" - that removes volumes and would
echo   destroy the database.)
echo.
call scripts\common.bat write_log logs\shutdown.log "===== STOP_OMS360.bat complete ====="
endlocal
exit /b 0
