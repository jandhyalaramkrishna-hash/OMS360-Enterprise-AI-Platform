@echo off
setlocal
REM NOTE: this file lives in scripts\, not the repo root. %~dp0 here is the
REM scripts\ folder itself - the previous version did `cd /d "%~dp0"` and
REM then called `scripts\common.bat`, which would have looked for
REM scripts\scripts\common.bat (doesn't exist) the moment anyone actually
REM ran this file directly. Fixed by moving up one level to the repo root
REM before doing anything else, matching how START/STOP_OMS360.bat (which
REM live at the repo root) resolve their own paths.
cd /d "%~dp0.."
call scripts\common.bat init

echo.
echo =============================================================================
echo   OMS-360 Enterprise Order Management System - HEALTH CHECK
echo =============================================================================
echo.

call scripts\common.bat write_log logs\health.log "===== CHECK_OMS360.bat invoked ====="

REM --------------------------------------------------------------------------
REM Docker Desktop
REM --------------------------------------------------------------------------
echo -- Docker --------------------------------------------------------------
docker info >nul 2>&1
if errorlevel 1 (
    echo   Docker Desktop ........... NOT RUNNING
    call scripts\common.bat write_log logs\health.log "Docker Desktop: NOT RUNNING"
    echo.
    echo   Docker Desktop is not running - remaining checks skipped.
    call scripts\common.bat write_log logs\health.log "===== CHECK_OMS360.bat complete (Docker not running) ====="
    endlocal
    exit /b 1
) else (
    echo   Docker Desktop ........... RUNNING
    call scripts\common.bat write_log logs\health.log "Docker Desktop: RUNNING"
)

REM --------------------------------------------------------------------------
REM Infrastructure containers
REM --------------------------------------------------------------------------
echo.
echo -- Infrastructure --------------------------------------------------------
call scripts\common.bat check_container %MYSQL_CONTAINER%
echo   MySQL       (%MYSQL_CONTAINER%) .... %CONTAINER_STATE% / health=%CONTAINER_HEALTH%
call scripts\common.bat write_log logs\health.log "MySQL: %CONTAINER_STATE% / health=%CONTAINER_HEALTH%"

call scripts\common.bat check_container %ZOOKEEPER_CONTAINER%
echo   Zookeeper   (%ZOOKEEPER_CONTAINER%) .... %CONTAINER_STATE% / health=%CONTAINER_HEALTH%
call scripts\common.bat write_log logs\health.log "Zookeeper: %CONTAINER_STATE% / health=%CONTAINER_HEALTH%"

call scripts\common.bat check_container %KAFKA_CONTAINER%
echo   Kafka       (%KAFKA_CONTAINER%) .... %CONTAINER_STATE% / health=%CONTAINER_HEALTH%
call scripts\common.bat write_log logs\health.log "Kafka: %CONTAINER_STATE% / health=%CONTAINER_HEALTH%"

REM --------------------------------------------------------------------------
REM Application containers
REM --------------------------------------------------------------------------
echo.
echo -- Application -------------------------------------------------------------
call scripts\common.bat check_container %ENGINE_CONTAINER%
echo   Engine      (%ENGINE_CONTAINER%) .... %CONTAINER_STATE% / health=%CONTAINER_HEALTH%
call scripts\common.bat write_log logs\health.log "Engine: %CONTAINER_STATE% / health=%CONTAINER_HEALTH%"

call scripts\common.bat check_container %CONSUMER_CONTAINER%
echo   Consumer    (%CONSUMER_CONTAINER%) .... %CONTAINER_STATE% / health=%CONTAINER_HEALTH% (no HTTP endpoint - status is container state only)
call scripts\common.bat write_log logs\health.log "Consumer: %CONTAINER_STATE% / health=%CONTAINER_HEALTH%"

REM --------------------------------------------------------------------------
REM HTTP endpoints
REM --------------------------------------------------------------------------
echo.
echo -- Endpoints ---------------------------------------------------------------
call scripts\common.bat check_health
echo   Health API  (%HEALTH_URL%)
echo               HTTP=%HEALTH_HTTP%  reported status=%HEALTH_STATUS%
call scripts\common.bat write_log logs\health.log "Health API: HTTP=%HEALTH_HTTP% status=%HEALTH_STATUS%"

REM 2026-07-22 fix (DEC-0025): these three used to each run their own inline
REM `powershell -Command "... (Invoke-WebRequest ...).StatusCode ..."` FOR /F
REM block - the same cmd.exe paren-parsing crash fixed in :check_health /
REM :check_port (scripts\common.bat). Now calling the one shared, fixed
REM helper three times instead of repeating the bug three times.
call scripts\common.bat check_http_status %SWAGGER_URL%
set "SWAGGER_HTTP=%HTTP_STATUS_RESULT%"
echo   Swagger     (%SWAGGER_URL%) .... HTTP=%SWAGGER_HTTP%
call scripts\common.bat write_log logs\health.log "Swagger: HTTP=%SWAGGER_HTTP%"

call scripts\common.bat check_http_status %DASHBOARD_OPS_URL%
set "DASH_OPS_HTTP=%HTTP_STATUS_RESULT%"
echo   Ops Dashboard (%DASHBOARD_OPS_URL%) .... HTTP=%DASH_OPS_HTTP%
call scripts\common.bat write_log logs\health.log "Ops Dashboard: HTTP=%DASH_OPS_HTTP%"

call scripts\common.bat check_http_status %DASHBOARD_MON_URL%
set "DASH_MON_HTTP=%HTTP_STATUS_RESULT%"
echo   Mon Dashboard (%DASHBOARD_MON_URL%) .... HTTP=%DASH_MON_HTTP%
call scripts\common.bat write_log logs\health.log "Monitoring Dashboard: HTTP=%DASH_MON_HTTP%"

REM --------------------------------------------------------------------------
REM Docker network
REM --------------------------------------------------------------------------
echo.
echo -- Docker Network ------------------------------------------------------------
echo   Expected network (fixed) . %NETWORK_NAME%
call scripts\common.bat detect_network
if not "%DETECTED_NETWORK%"=="" (
    echo   mysql is attached to ..... %DETECTED_NETWORK%
    if /i not "%DETECTED_NETWORK%"=="%NETWORK_NAME%" (
        echo   [WARN] mysql is NOT on the expected network. It is likely an old
        echo          container from before the fixed-network fix - run
        echo          STOP_OMS360.bat then START_OMS360.bat to recreate it.
    )
    call scripts\common.bat write_log logs\health.log "Detected network: %DETECTED_NETWORK%"
) else (
    echo   mysql is attached to ..... UNKNOWN ^(mysql container not found/running^)
    call scripts\common.bat write_log logs\health.log "Detected network: UNKNOWN"
)

REM --------------------------------------------------------------------------
REM Port usage
REM --------------------------------------------------------------------------
echo.
echo -- Port Usage ----------------------------------------------------------------
call scripts\common.bat check_port %MYSQL_PORT%
echo   %MYSQL_PORT% (MySQL) ..................... %PORT_STATUS%
call scripts\common.bat check_port %ZOOKEEPER_PORT%
echo   %ZOOKEEPER_PORT% (Zookeeper) ................. %PORT_STATUS%
call scripts\common.bat check_port %KAFKA_PORT%
echo   %KAFKA_PORT% (Kafka) .................... %PORT_STATUS%
call scripts\common.bat check_port %ENGINE_PORT%
echo   %ENGINE_PORT% (Engine/API) ............... %PORT_STATUS%
call scripts\common.bat write_log logs\health.log "Port check complete (mysql/zookeeper/kafka/engine)"

echo.
echo =============================================================================
echo   Health report complete. Full history in logs\health.log
echo =============================================================================
call scripts\common.bat write_log logs\health.log "===== CHECK_OMS360.bat complete ====="
endlocal
exit /b 0
