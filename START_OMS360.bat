@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
call scripts\common.bat init

echo.
echo =============================================================================
echo   OMS-360 Enterprise Order Management System - START
echo =============================================================================
echo.

call scripts\common.bat write_log logs\startup.log "===== START_OMS360.bat invoked ====="

REM --------------------------------------------------------------------------
REM 1. Docker Desktop check
REM --------------------------------------------------------------------------
echo [1/7] Checking Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo   [FAIL] Docker Desktop is not running or not installed.
    echo          Start Docker Desktop and re-run this script.
    call scripts\common.bat write_log logs\startup.log "FAILED: Docker Desktop not running"
    goto :fail_exit
)
echo   [OK] Docker Desktop is running.
call scripts\common.bat write_log logs\startup.log "Docker Desktop check OK"

REM --------------------------------------------------------------------------
REM 2. Clean up any previous OMS360 environment BEFORE starting anything new.
REM
REM 2026-07-28 addition (see docs/governance/DECISION-LOG.md DEC-0042): this
REM is the fix for
REM   Error response from daemon: ports are not available: 0.0.0.0:3306
REM   bind: Only one usage of each socket address is normally permitted.
REM The most common cause is a leftover/orphaned OMS360 container (or a
REM container sharing OMS360's fixed name from a previous partial run)
REM still holding the port. scripts\common.bat's new
REM :cleanup_previous_environment runs `docker compose down --remove-orphans`
REM plus a belt-and-suspenders per-container `docker rm -f` and an unused-
REM network removal - see that subroutine's own header comment for detail.
REM Scoped strictly to OMS360's own fixed container/network names, exactly
REM like every other launcher script in this project (never touches another
REM Docker project on the machine).
REM
REM Deliberately run BEFORE the port-freeing step (3) below - not after, as
REM a literal top-to-bottom reading of the original request would order it
REM - so ports 3306/2181/9092/8000 are already released by removing OUR OWN
REM leftover containers first, via Docker itself. Step 3 then only ever has
REM to identify and terminate a genuinely external process (a native
REM Windows MySQL service, a different Docker project, etc.).
REM --------------------------------------------------------------------------
echo [2/7] Cleaning up any previous OMS360 environment...
call scripts\common.bat cleanup_previous_environment
echo   [OK] Previous OMS360 containers/network cleaned up ^(if any existed^).
call scripts\common.bat write_log logs\startup.log "Previous environment cleanup complete"

REM --------------------------------------------------------------------------
REM 3. Check every port OMS360 needs and release stale processes still
REM    holding them, per DEC-0042. Runs after step 2, so anything this step
REM    finds occupying a port is - by construction - not one of OMS360's own
REM    containers (those were already removed above).
REM --------------------------------------------------------------------------
echo [3/7] Checking OMS360 ports ^(3306, 2181, 9092, 8000^)...
call scripts\common.bat free_port %MYSQL_PORT% "MySQL 3306"
call scripts\common.bat free_port %ZOOKEEPER_PORT% "Zookeeper 2181"
call scripts\common.bat free_port %KAFKA_PORT% "Kafka 9092"
call scripts\common.bat free_port %ENGINE_PORT% "Engine API 8000"

REM --------------------------------------------------------------------------
REM 4. Bring up the full stack (mysql, zookeeper, kafka, engine, consumer)
REM    via a single docker compose command.
REM
REM    This never touches any other Docker project on the machine - Compose
REM    scopes `up`/`stop`/`down` strictly to the services defined in
REM    %COMPOSE_FILE%. It is also fully idempotent: any service that is
REM    already running and unchanged is left alone; only what's missing,
REM    stopped, or out of date (e.g. the engine/consumer images after a code
REM    change) gets (re)created.
REM
REM    --build       rebuild the engine/consumer images if the Dockerfile or
REM                   build context changed.
REM    --wait         block until every service with a healthcheck reports
REM                   healthy (mysql, zookeeper, kafka, engine), honoring the
REM                   depends_on/condition graph in docker-compose.yml, and
REM                   return a non-zero exit code if anything goes unhealthy.
REM                   This is the literal implementation of "wait until
REM                   MySQL becomes healthy instead of assuming it is ready"
REM                   - Docker itself polls each service's own HEALTHCHECK
REM                   (mysqladmin ping for MySQL) rather than this script
REM                   guessing a fixed sleep duration.
REM    --wait-timeout give the whole stack up to 5 minutes (first run also
REM                   has to build two images and pull mysql/zk/kafka on a
REM                   cold Docker cache).
REM --------------------------------------------------------------------------
echo [4/7] Starting OMS360 stack ^(mysql, zookeeper, kafka, engine, consumer^)...
echo       Waiting for Docker's own health checks to confirm each service is
echo       actually ready - never assumed. This can take a few minutes on
echo       first run ^(image pulls + build^).
call scripts\common.bat write_log logs\startup.log "Running: docker compose -f %COMPOSE_FILE% up -d --build --wait"
docker compose -f %COMPOSE_FILE% up -d --build --wait --wait-timeout 300
set "COMPOSE_RESULT=%ERRORLEVEL%"

if not "%COMPOSE_RESULT%"=="0" (
    echo.
    echo   [FAIL] docker compose up did not reach a healthy state within the timeout.
    call scripts\common.bat write_log logs\startup.log "FAILED: docker compose up --wait returned %COMPOSE_RESULT%"

    set "FAILED_SERVICE="
    echo.
    echo   Per-service status:

    call scripts\common.bat check_container %MYSQL_CONTAINER%
    echo     MySQL       ^(%MYSQL_CONTAINER%^) ..... %CONTAINER_STATE% / %CONTAINER_HEALTH%
    if not defined FAILED_SERVICE if not "%CONTAINER_STATE%"=="RUNNING" set "FAILED_SERVICE=MySQL"
    if not defined FAILED_SERVICE if /i not "%CONTAINER_HEALTH%"=="healthy" if not "%CONTAINER_HEALTH%"=="NONE" set "FAILED_SERVICE=MySQL"

    call scripts\common.bat check_container %ZOOKEEPER_CONTAINER%
    echo     Zookeeper   ^(%ZOOKEEPER_CONTAINER%^) ..... %CONTAINER_STATE% / %CONTAINER_HEALTH%
    if not defined FAILED_SERVICE if not "%CONTAINER_STATE%"=="RUNNING" set "FAILED_SERVICE=Zookeeper"
    if not defined FAILED_SERVICE if /i not "%CONTAINER_HEALTH%"=="healthy" if not "%CONTAINER_HEALTH%"=="NONE" set "FAILED_SERVICE=Zookeeper"

    call scripts\common.bat check_container %KAFKA_CONTAINER%
    echo     Kafka       ^(%KAFKA_CONTAINER%^) ..... %CONTAINER_STATE% / %CONTAINER_HEALTH%
    if not defined FAILED_SERVICE if not "%CONTAINER_STATE%"=="RUNNING" set "FAILED_SERVICE=Kafka"
    if not defined FAILED_SERVICE if /i not "%CONTAINER_HEALTH%"=="healthy" if not "%CONTAINER_HEALTH%"=="NONE" set "FAILED_SERVICE=Kafka"

    call scripts\common.bat check_container %ENGINE_CONTAINER%
    echo     Engine/API  ^(%ENGINE_CONTAINER%^) ..... %CONTAINER_STATE% / %CONTAINER_HEALTH%
    if not defined FAILED_SERVICE if not "%CONTAINER_STATE%"=="RUNNING" set "FAILED_SERVICE=Engine/API"
    if not defined FAILED_SERVICE if /i not "%CONTAINER_HEALTH%"=="healthy" if not "%CONTAINER_HEALTH%"=="NONE" set "FAILED_SERVICE=Engine/API"

    call scripts\common.bat check_container %CONSUMER_CONTAINER%
    echo     Consumer    ^(%CONSUMER_CONTAINER%^) ..... %CONTAINER_STATE% ^(no HTTP health endpoint^)
    if not defined FAILED_SERVICE if not "%CONTAINER_STATE%"=="RUNNING" set "FAILED_SERVICE=Consumer"

    echo.
    if defined FAILED_SERVICE (
        echo   ROOT CAUSE: %FAILED_SERVICE% failed to start or become healthy.
        call scripts\common.bat write_log logs\startup.log "FAILED SERVICE: %FAILED_SERVICE%"
    ) else (
        echo   All 5 containers report RUNNING/healthy individually, but the
        echo   overall docker compose up --wait call still returned an error -
        echo   see the diagnostics below and logs\startup.log for detail.
    )

    echo.
    echo   Current container status:
    docker compose -f %COMPOSE_FILE% ps
    call scripts\common.bat dump_diagnostics %MYSQL_CONTAINER%
    call scripts\common.bat dump_diagnostics %ZOOKEEPER_CONTAINER%
    call scripts\common.bat dump_diagnostics %KAFKA_CONTAINER%
    call scripts\common.bat dump_diagnostics %ENGINE_CONTAINER%
    call scripts\common.bat dump_diagnostics %CONSUMER_CONTAINER%
    goto :fail_exit
)
echo   [OK] All services report healthy.
call scripts\common.bat write_log logs\startup.log "docker compose up --wait succeeded"

REM --------------------------------------------------------------------------
REM 5. Explicit per-service confirmation (belt-and-suspenders on top of
REM    --wait above) so the summary below is always accurate even if a
REM    service flips state right after --wait returned.
REM --------------------------------------------------------------------------
echo [5/7] Verifying each container...

call scripts\common.bat check_container %MYSQL_CONTAINER%
set "MYSQL_STATE=%CONTAINER_STATE%"
set "MYSQL_HEALTH=%CONTAINER_HEALTH%"
echo   MySQL       (%MYSQL_CONTAINER%) ..... %MYSQL_STATE% / %MYSQL_HEALTH%

call scripts\common.bat check_container %ZOOKEEPER_CONTAINER%
set "ZK_STATE=%CONTAINER_STATE%"
set "ZK_HEALTH=%CONTAINER_HEALTH%"
echo   Zookeeper   (%ZOOKEEPER_CONTAINER%) ..... %ZK_STATE% / %ZK_HEALTH%

call scripts\common.bat check_container %KAFKA_CONTAINER%
set "KAFKA_STATE=%CONTAINER_STATE%"
set "KAFKA_HEALTH=%CONTAINER_HEALTH%"
echo   Kafka       (%KAFKA_CONTAINER%) ..... %KAFKA_STATE% / %KAFKA_HEALTH%

call scripts\common.bat check_container %ENGINE_CONTAINER%
set "ENGINE_STATE=%CONTAINER_STATE%"
set "ENGINE_HEALTH=%CONTAINER_HEALTH%"
echo   Engine      (%ENGINE_CONTAINER%) ..... %ENGINE_STATE% / %ENGINE_HEALTH%

call scripts\common.bat check_container %CONSUMER_CONTAINER%
set "CONSUMER_STATE=%CONTAINER_STATE%"
echo   Consumer    (%CONSUMER_CONTAINER%) ..... %CONSUMER_STATE% (no HTTP health endpoint)

if not "%MYSQL_STATE%"=="RUNNING" (
    echo   [FAIL] MySQL is not running.
    call scripts\common.bat write_log logs\startup.log "FAILED: MySQL not RUNNING after compose up --wait"
    goto :fail_exit
)
if not "%ZK_STATE%"=="RUNNING" (
    echo   [FAIL] Zookeeper is not running.
    call scripts\common.bat write_log logs\startup.log "FAILED: Zookeeper not RUNNING after compose up --wait"
    goto :fail_exit
)
if not "%KAFKA_STATE%"=="RUNNING" (
    echo   [FAIL] Kafka is not running.
    call scripts\common.bat write_log logs\startup.log "FAILED: Kafka not RUNNING after compose up --wait"
    goto :fail_exit
)
if not "%ENGINE_STATE%"=="RUNNING" (
    echo   [FAIL] Engine is not running.
    call scripts\common.bat write_log logs\startup.log "FAILED: Engine not RUNNING after compose up --wait"
    goto :fail_exit
)
if not "%CONSUMER_STATE%"=="RUNNING" (
    echo   [FAIL] Consumer is not running.
    call scripts\common.bat write_log logs\startup.log "FAILED: Consumer not RUNNING after compose up --wait"
    goto :fail_exit
)
call scripts\common.bat write_log logs\startup.log "All 5 containers RUNNING"

REM --------------------------------------------------------------------------
REM 6. Confirm the Engine's /health endpoint directly (belt-and-suspenders on
REM    top of its Docker healthcheck).
REM --------------------------------------------------------------------------
echo [6/7] Confirming Engine health endpoint (%HEALTH_URL%)...
call scripts\common.bat check_health
if not "%HEALTH_HTTP%"=="200" (
    echo   [FAIL] Engine health endpoint did not return HTTP 200 ^(got %HEALTH_HTTP%^).
    call scripts\common.bat write_log logs\startup.log "FAILED: engine health HTTP=%HEALTH_HTTP%"
    call scripts\common.bat dump_diagnostics %ENGINE_CONTAINER%
    goto :fail_exit
)
echo   [OK] Engine is responding. Reported status: %HEALTH_STATUS%
call scripts\common.bat write_log logs\startup.log "Engine health OK (HTTP 200, status=%HEALTH_STATUS%)"
if not "%HEALTH_STATUS%"=="HEALTHY" (
    echo   [WARN] Engine is up but reporting "%HEALTH_STATUS%" - a dependency
    echo          ^(Kafka/disk/memory/CPU^) may be degraded. Check %DASHBOARD_MON_URL%
    call scripts\common.bat write_log logs\startup.log "WARNING: engine status is %HEALTH_STATUS%, not HEALTHY"
)

REM --------------------------------------------------------------------------
REM 7. Open Swagger + the Inventory dashboard, print summary
REM
REM 2026-07-25 fix: launch msedge.exe directly (by its installed path)
REM instead of relying only on the "microsoft-edge:" URI protocol handler.
REM The URI-handler approach can silently open nothing on machines where
REM that protocol association isn't registered/allowed - invoking
REM msedge.exe directly with the URL as an argument is the more reliable
REM way to force Edge specifically. Falls back to the microsoft-edge: URI
REM handler only if msedge.exe isn't found in either standard install
REM location.
REM --------------------------------------------------------------------------
echo [7/7] Opening Swagger and the Inventory dashboard in Microsoft Edge...

set "EDGE_EXE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE_EXE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined EDGE_EXE if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "EDGE_EXE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

REM 2026-07-27 change (see docs/governance/DECISION-LOG.md): Product Owner
REM asked for exactly two tabs on startup instead of the previous three
REM (Swagger + Operations + Monitoring) - Swagger for the API, and the
REM Inventory dashboard as the one "UI" tab, since that's the page
REM actively being used/tested. Operations/Monitoring/AI Copilot are still
REM fully reachable via each dashboard's own nav bar - they just don't
REM auto-open anymore.
if defined EDGE_EXE (
    start "" "%EDGE_EXE%" "%SWAGGER_URL%"
    start "" "%EDGE_EXE%" "%DASHBOARD_INV_URL%"
    call scripts\common.bat write_log logs\startup.log "Opened Swagger and the Inventory dashboard via msedge.exe"
) else (
    echo   [WARN] msedge.exe not found in the usual install locations - using the microsoft-edge: URI handler instead.
    start "" microsoft-edge:%SWAGGER_URL%
    start "" microsoft-edge:%DASHBOARD_INV_URL%
    call scripts\common.bat write_log logs\startup.log "Opened Swagger and the Inventory dashboard via microsoft-edge: URI handler (msedge.exe not found)"
)

echo.
echo =============================================================================
echo   OMS-360 STARTUP SUMMARY
echo =============================================================================
echo   Docker Desktop ........... RUNNING
echo   MySQL (%MYSQL_CONTAINER%) ..... %MYSQL_STATE% / %MYSQL_HEALTH%
echo   Zookeeper (%ZOOKEEPER_CONTAINER%) . %ZK_STATE% / %ZK_HEALTH%
echo   Kafka (%KAFKA_CONTAINER%) ....... %KAFKA_STATE% / %KAFKA_HEALTH%
echo   Docker Network ............ %NETWORK_NAME%
echo   API / Engine (%ENGINE_CONTAINER%) RUNNING - status: %HEALTH_STATUS%
echo   Consumer (%CONSUMER_CONTAINER%)  %CONSUMER_STATE%
echo   Ports verified ............ 3306, 2181, 9092, 8000
echo.
echo   Swagger ................... %SWAGGER_URL%
echo   Dashboard .................. %DASHBOARD_INV_URL%
echo   Health API ................ %HEALTH_URL%
echo   (Operations/Monitoring/AI Copilot are reachable from the nav bar on any dashboard page)
echo =============================================================================
echo.
call scripts\common.bat write_log logs\startup.log "===== STARTUP SUMMARY: SUCCESS (engine status=%HEALTH_STATUS%) ====="

REM --------------------------------------------------------------------------
REM 2026-07-28 addition (see DEC-0042): explicitly return to the project
REM root before the final banner/prompt. Note this only guarantees the
REM *cmd.exe process this .bat runs in* ends up here - if this script is
REM invoked as `.\START_OMS360.bat` from a PowerShell window, that .bat
REM runs as a child cmd.exe process, and a child process's `cd` can never
REM change its parent PowerShell session's working directory. In practice
REM this is a non-issue: PowerShell's own prompt simply stays wherever it
REM already was (this repository root, if that's where the script was
REM launched from), which is exactly the desired end state.
REM --------------------------------------------------------------------------
cd /d "%~dp0"

echo.
echo ============================================================
echo OMS360 is Ready!
echo.
echo Swagger  : %SWAGGER_URL%
echo Dashboard: %DASHBOARD_INV_URL%
echo.
echo MySQL Console:
echo docker exec -it oms360_mysql mysql -uroot -proot123 oms360_db
echo ============================================================
echo.
pause
goto :end

:fail_exit
echo.
echo =============================================================================
echo   STARTUP FAILED - see logs\startup.log and the diagnostics above for details
echo =============================================================================
call scripts\common.bat write_log logs\startup.log "===== STARTUP SUMMARY: FAILED ====="
cd /d "%~dp0"
endlocal
exit /b 1

:end
endlocal
exit /b 0
