@echo off
setlocal
cd /d "%~dp0.."
call scripts\common.bat init

echo.
echo =============================================================================
echo   OMS-360 Enterprise Order Management System - RESTART
echo   Restarting the application layer only ^(Engine + Consumer^).
echo   MySQL, Zookeeper, and Kafka are left running.
echo =============================================================================
echo.

call scripts\common.bat write_log logs\startup.log "===== RESTART_OMS360.bat invoked ====="
call scripts\common.bat write_log logs\shutdown.log "===== RESTART_OMS360.bat invoked (stop phase) ====="

call STOP_OMS360.bat
if errorlevel 1 (
    echo   [FAIL] Stop phase failed. Aborting restart - see logs\shutdown.log.
    call scripts\common.bat write_log logs\startup.log "RESTART ABORTED: stop phase failed"
    endlocal
    exit /b 1
)

echo.
echo Stop phase complete. Starting application layer again...
echo.

REM START_OMS360.bat runs `docker compose up -d --build --wait` against the
REM single, unified docker-compose.yml. Because mysql/zookeeper/kafka are
REM already running and unchanged, Compose leaves them alone - only the
REM just-stopped engine/consumer containers are rebuilt and restarted. No
REM separate "app-only" compose file or flag is needed for this to be safe.
call START_OMS360.bat
set "START_RESULT=%ERRORLEVEL%"

if "%START_RESULT%"=="0" (
    echo.
    echo   [OK] Restart complete.
    call scripts\common.bat write_log logs\startup.log "===== RESTART_OMS360.bat complete: SUCCESS ====="
) else (
    echo.
    echo   [FAIL] Restart's start phase failed - see logs\startup.log.
    call scripts\common.bat write_log logs\startup.log "===== RESTART_OMS360.bat complete: FAILED ====="
)

endlocal
exit /b %START_RESULT%
