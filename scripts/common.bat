@echo off
REM =============================================================================
REM common.bat - Shared constants and helper subroutines for the OMS360
REM launcher scripts (START/STOP/RESTART/CHECK_OMS360.bat).
REM
REM This file is a LIBRARY. It is not meant to be double-clicked or run on
REM its own - it is loaded by the other scripts via:
REM     call scripts\common.bat init
REM     call scripts\common.bat detect_network
REM     call scripts\common.bat write_log logs\startup.log "message"
REM
REM Fixed in the 2026-07-21 infrastructure audit:
REM   - THE BATCH LABEL BUG ("The system cannot find the batch label
REM     specified"): every caller used to invoke this file as
REM     `call scripts\common.bat :init` (colon included in the argument).
REM     Below, the dispatcher builds `goto :%SUB%`, which - once %SUB%
REM     already contains a leading colon - expands to `goto ::init`
REM     (double colon). Whether that resolves correctly is inconsistent
REM     across Windows/cmd.exe builds, and is exactly the class of bug that
REM     produces "cannot find the batch label specified" intermittently.
REM     Fixed two ways, belt-and-suspenders:
REM       1) The dispatcher now strips a leading colon from the incoming
REM          argument if present, so `goto :%SUB%` always expands to
REM          exactly one colon no matter how it's called.
REM       2) Every caller (START/STOP/RESTART/CHECK_OMS360.bat) was updated
REM          to call `call scripts\common.bat init` (no leading colon) for
REM          clarity - but common.bat itself no longer depends on callers
REM          getting that right.
REM   - The Docker network name is now a FIXED constant (oms360_network,
REM     matching the `networks:` block added to docker-compose.yml) instead
REM     of something that had to be discovered at runtime via
REM     `docker inspect`. :detect_network is kept only as an optional,
REM     non-load-bearing diagnostic (used by CHECK_OMS360.bat to confirm the
REM     running mysql container is actually attached to the network we
REM     expect) - nothing depends on it succeeding anymore.
REM   - Added :dump_diagnostics <container> - prints the tail of a
REM     container's logs plus its inspected state, for clear failure
REM     diagnostics from START_OMS360.bat.
REM
REM 2026-07-28 addition (see docs/governance/DECISION-LOG.md DEC-0042):
REM   Made START_OMS360.bat fully self-healing against
REM   "ports are not available: 0.0.0.0:3306 ... Only one usage of each
REM   socket address is normally permitted" and stale leftover containers.
REM   Four new subroutines added below, all called only from
REM   START_OMS360.bat's new steps [2/7] and [3/7]:
REM     :cleanup_previous_environment - docker compose down --remove-orphans,
REM       force-removes any leftover container under this project's fixed
REM       names, removes an unused oms360_network if present.
REM     :find_pid_on_port <port>            - sets PORT_PID
REM     :get_process_name <pid>             - sets PROC_NAME
REM     :free_port <port> <friendly-label>  - finds+prints+terminates
REM       whatever process is still bound to a required port, then
REM       re-verifies the port is actually free.
REM   All four are pure netstat/tasklist/taskkill/docker calls with no
REM   inline PowerShell -Command one-liners, so none of them are exposed to
REM   the cmd.exe FOR /F paren-parsing crash documented below on
REM   :check_port/:check_health (DEC-0025) - there simply are no parentheses
REM   inside any backquoted command here to trip over.
REM
REM All values below (container names, ports, paths) were verified against
REM the actual source in this project - docker-compose.yml, app/config.py,
REM app/main.py, app/routes/health.py.
REM =============================================================================

if "%~1"=="" (
    echo [common.bat] This file is a shared library. Run START_OMS360.bat instead.
    exit /b 1
)

set "SUB=%~1"
if "%SUB:~0,1%"==":" set "SUB=%SUB:~1%"
shift
goto :%SUB%

REM -----------------------------------------------------------------------
REM :init - sets every shared constant used across the launcher scripts.
REM   - MySQL container:      oms360_mysql       (port 3306)
REM   - Zookeeper container:  oms360_zookeeper   (port 2181)
REM   - Kafka container:      oms360_kafka       (external port 9092, internal 29092)
REM   - Engine container:     oms360_core_engine (port 8000, GET /health)
REM   - Consumer container:   oms360_consumer    (no exposed port, no HTTP health)
REM -----------------------------------------------------------------------
:init
set "MYSQL_CONTAINER=oms360_mysql"
set "ZOOKEEPER_CONTAINER=oms360_zookeeper"
set "KAFKA_CONTAINER=oms360_kafka"
set "ENGINE_CONTAINER=oms360_core_engine"
set "CONSUMER_CONTAINER=oms360_consumer"

set "MYSQL_PORT=3306"
set "ZOOKEEPER_PORT=2181"
set "KAFKA_PORT=9092"
set "ENGINE_PORT=8000"

set "HEALTH_PATH=/health"
set "SWAGGER_PATH=/docs"
set "DASHBOARD_OPS_PATH=/dashboard/operations"
set "DASHBOARD_MON_PATH=/dashboard/monitoring"
set "DASHBOARD_INV_PATH=/dashboard/inventory"
set "DASHBOARD_COPILOT_PATH=/dashboard/ai-copilot"
set "METRICS_PATH=/metrics"

set "BASE_URL=http://localhost:%ENGINE_PORT%"
set "HEALTH_URL=%BASE_URL%%HEALTH_PATH%"
set "SWAGGER_URL=%BASE_URL%%SWAGGER_PATH%"
set "DASHBOARD_OPS_URL=%BASE_URL%%DASHBOARD_OPS_PATH%"
set "DASHBOARD_MON_URL=%BASE_URL%%DASHBOARD_MON_PATH%"
set "DASHBOARD_INV_URL=%BASE_URL%%DASHBOARD_INV_PATH%"
set "DASHBOARD_COPILOT_URL=%BASE_URL%%DASHBOARD_COPILOT_PATH%"

set "COMPOSE_FILE=docker-compose.yml"
REM Kept only for the legacy/optional docker\docker-compose.app.yml path -
REM not used by the current START/STOP/RESTART scripts.
set "COMPOSE_APP_FILE=docker\docker-compose.app.yml"

REM Fixed network name - see the `networks:` block in docker-compose.yml.
set "NETWORK_NAME=oms360_network"

exit /b 0

REM -----------------------------------------------------------------------
REM :timestamp - sets TS to "yyyy-MM-dd HH:mm:ss", locale-independent
REM (uses PowerShell rather than DATE/TIME, which are locale-dependent
REM and unreliable to parse in batch).
REM -----------------------------------------------------------------------
:timestamp
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"`) do set "TS=%%T"
exit /b 0

REM -----------------------------------------------------------------------
REM :write_log <logfile-relative-path> <message>
REM Appends "[timestamp] message" to the given log file under logs\.
REM Creates the logs\ folder if it does not exist.
REM -----------------------------------------------------------------------
:write_log
set "LOGFILE=%~1"
set "MSG=%~2"
if not exist "%~dp0..\logs" mkdir "%~dp0..\logs" >nul 2>&1
call :timestamp
echo [%TS%] %MSG% >> "%~dp0..\%LOGFILE%"
exit /b 0

REM -----------------------------------------------------------------------
REM :detect_network - DIAGNOSTIC ONLY. Confirms the network oms360_mysql is
REM actually attached to, and sets DETECTED_NETWORK to it. With the fixed
REM `oms360_network` name now declared in docker-compose.yml, this should
REM always equal %NETWORK_NAME% once the stack has been started at least
REM once with the current compose file. A mismatch here is a useful signal
REM (e.g. an old container from before this fix is still running) but is
REM never required to succeed for START/STOP/RESTART to work.
REM -----------------------------------------------------------------------
:detect_network
set "DETECTED_NETWORK="
docker inspect %MYSQL_CONTAINER% >nul 2>&1
if errorlevel 1 exit /b 1
for /f "usebackq delims=" %%N in (`docker inspect %MYSQL_CONTAINER% --format "{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}" 2^>nul`) do set "DETECTED_NETWORK=%%N"
if "%DETECTED_NETWORK%"=="" exit /b 1
exit /b 0

REM -----------------------------------------------------------------------
REM :check_container <container_name>
REM Sets CONTAINER_STATE to RUNNING, STOPPED, or MISSING.
REM Sets CONTAINER_HEALTH to the Docker healthcheck status if the container
REM defines one (healthy/unhealthy/starting), or NONE if it has no
REM healthcheck defined (true for consumer only now - mysql, zookeeper,
REM kafka, and engine all define healthchecks as of this fix).
REM -----------------------------------------------------------------------
:check_container
set "CC_NAME=%~1"
set "CONTAINER_STATE=MISSING"
set "CONTAINER_HEALTH=NONE"
docker inspect %CC_NAME% >nul 2>&1
if errorlevel 1 exit /b 0
for /f "usebackq delims=" %%S in (`docker inspect %CC_NAME% --format "{{.State.Status}}" 2^>nul`) do set "RAW_STATE=%%S"
if /i "%RAW_STATE%"=="running" (set "CONTAINER_STATE=RUNNING") else (set "CONTAINER_STATE=STOPPED")
for /f "usebackq delims=" %%H in (`docker inspect %CC_NAME% --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}NONE{{end}}" 2^>nul`) do set "CONTAINER_HEALTH=%%H"
exit /b 0

REM -----------------------------------------------------------------------
REM :check_port <port>
REM Sets PORT_STATUS to OPEN or CLOSED by testing a TCP connection to
REM localhost:<port> via PowerShell.
REM
REM 2026-07-22 fix (see docs/governance/DECISION-LOG.md DEC-0025): this used
REM to run PowerShell inline via
REM   for /f ... in (`powershell -Command "try { $c = New-Object ...; $c.Connect('localhost', %CP_PORT%); ... }"`)
REM which crashes cmd.exe's FOR /F "in (...)" parser with the literal
REM message ". was unexpected at this time." - the unescaped parentheses in
REM `New-Object ...`, `.Connect(...)`, and `.Close()` inside the backquoted
REM PowerShell one-liner confuse cmd's own paren-matching for the outer
REM `in (...)` clause. This is a well-known cmd.exe FOR /F pitfall, and it
REM is exactly the failure the Product Owner hit running START_OMS360.bat
REM (via :check_health below, which had the identical pattern). Fixed the
REM same way in both places: write the PowerShell logic to a small temp
REM .ps1 file and invoke it with `-File` instead of inline `-Command` - a
REM plain file path has no parentheses for cmd to trip on. The .ps1 prints
REM "VARNAME=value" lines, which `for /f "tokens=1,2 delims=="` turns
REM directly into `set "VARNAME=value"` - no delayed expansion required,
REM so this keeps working regardless of whether the calling script has
REM `setlocal EnableDelayedExpansion` on or off.
REM -----------------------------------------------------------------------
:check_port
set "CP_PORT=%~1"
set "PORT_STATUS=CLOSED"
set "CP_PS1=%TEMP%\oms360_check_port_%RANDOM%.ps1"
(
    echo $result = 'CLOSED'
    echo try {
    echo     $c = New-Object System.Net.Sockets.TcpClient
    echo     $c.Connect^('localhost', %CP_PORT%^)
    echo     $c.Close^(^)
    echo     $result = 'OPEN'
    echo } catch {
    echo     $result = 'CLOSED'
    echo }
    echo Write-Output "PORT_STATUS=$result"
) > "%CP_PS1%"
for /f "usebackq tokens=1,2 delims==" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%CP_PS1%" 2^>nul`) do set "%%A=%%B"
del /q "%CP_PS1%" >nul 2>&1
exit /b 0

REM -----------------------------------------------------------------------
REM :check_health
REM Calls GET %HEALTH_URL% and sets:
REM   HEALTH_HTTP   - HTTP status code, or "NOHTTP" if unreachable
REM   HEALTH_STATUS - the "status" field from the JSON body (HEALTHY /
REM                   WARNING / DEGRADED), or "UNKNOWN" if unreachable/
REM                   unparsable
REM Note: /health in this app always returns HTTP 200 even when
REM status=DEGRADED, so HEALTH_HTTP=200 alone does NOT mean everything is
REM healthy - HEALTH_STATUS must also be checked.
REM
REM 2026-07-22 fix: see the long comment on :check_port above - same
REM cmd.exe FOR /F paren-parsing crash, same temp-.ps1-file fix. This was
REM the actual call site that broke START_OMS360.bat's "[4/5] Confirming
REM Engine health endpoint" step with ". was unexpected at this time."
REM -----------------------------------------------------------------------
:check_health
set "HEALTH_HTTP=NOHTTP"
set "HEALTH_STATUS=UNKNOWN"
set "HC_PS1=%TEMP%\oms360_check_health_%RANDOM%.ps1"
(
    echo $code = 'NOHTTP'
    echo $status = 'UNKNOWN'
    echo try {
    echo     $r = Invoke-WebRequest -Uri '%HEALTH_URL%' -UseBasicParsing -TimeoutSec 5
    echo     $code = [string]$r.StatusCode
    echo     try { $status = ^($r.Content ^| ConvertFrom-Json^).status } catch { $status = 'UNKNOWN' }
    echo } catch {
    echo     $code = 'NOHTTP'
    echo }
    echo Write-Output "HEALTH_HTTP=$code"
    echo Write-Output "HEALTH_STATUS=$status"
) > "%HC_PS1%"
for /f "usebackq tokens=1,2 delims==" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%HC_PS1%" 2^>nul`) do set "%%A=%%B"
del /q "%HC_PS1%" >nul 2>&1
exit /b 0

REM -----------------------------------------------------------------------
REM :check_http_status <url>
REM Sets HTTP_STATUS_RESULT to the HTTP status code returned by a GET to
REM <url>, or "NOHTTP" if unreachable within 5 seconds. Introduced
REM 2026-07-22 to replace THREE duplicated, individually-broken inline
REM PowerShell FOR /F blocks in scripts\CHECK_OMS360.bat (Swagger, Ops
REM Dashboard, Monitoring Dashboard reachability) that had the identical
REM cmd.exe paren-parsing crash described on :check_port above - one
REM shared, fixed helper here instead of three copies of the same bug.
REM -----------------------------------------------------------------------
:check_http_status
set "CHS_URL=%~1"
set "HTTP_STATUS_RESULT=NOHTTP"
set "CHS_PS1=%TEMP%\oms360_check_http_%RANDOM%.ps1"
(
    echo $code = 'NOHTTP'
    echo try {
    echo     $r = Invoke-WebRequest -Uri '%CHS_URL%' -UseBasicParsing -TimeoutSec 5
    echo     $code = [string]$r.StatusCode
    echo } catch {
    echo     $code = 'NOHTTP'
    echo }
    echo Write-Output "HTTP_STATUS_RESULT=$code"
) > "%CHS_PS1%"
for /f "usebackq tokens=1,2 delims==" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%CHS_PS1%" 2^>nul`) do set "%%A=%%B"
del /q "%CHS_PS1%" >nul 2>&1
exit /b 0

REM -----------------------------------------------------------------------
REM :dump_diagnostics <container_name>
REM Prints the container's current state/health plus its last 40 log lines.
REM Used on failure paths so a failed start actually tells you why.
REM -----------------------------------------------------------------------
:dump_diagnostics
set "DD_NAME=%~1"
echo.
echo   ---- Diagnostics: %DD_NAME% ----------------------------------------------
docker inspect %DD_NAME% >nul 2>&1
if errorlevel 1 (
    echo   Container %DD_NAME% does not exist.
    exit /b 0
)
for /f "usebackq delims=" %%S in (`docker inspect %DD_NAME% --format "{{.State.Status}}" 2^>nul`) do echo   State: %%S
for /f "usebackq delims=" %%H in (`docker inspect %DD_NAME% --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}NONE{{end}}" 2^>nul`) do echo   Health: %%H
echo   Last 40 log lines:
docker logs --tail 40 %DD_NAME% 2>&1
echo   ---------------------------------------------------------------------------
exit /b 0

REM -----------------------------------------------------------------------
REM :cleanup_previous_environment
REM Added 2026-07-28 (see docs/governance/DECISION-LOG.md DEC-0042).
REM
REM Removes any previous OMS360 Docker environment before a fresh start:
REM   1. `docker compose down --remove-orphans` - the normal, scoped way to
REM      tear down every container + the network this compose file defines,
REM      plus any orphaned container Compose recognizes as belonging to
REM      this project. Never touches any other Docker project.
REM   2. A belt-and-suspenders `docker rm -f` on each of this project's
REM      fixed container names (oms360_mysql, oms360_zookeeper, etc.) if
REM      still present after step 1 - covers the case of a container
REM      sharing OMS360's fixed name but not tracked as part of this
REM      compose project (e.g. started once from a different working
REM      directory), which step 1 alone would not remove. This is the
REM      single most common real-world cause of the reported
REM      "ports are not available: 0.0.0.0:3306 ... Only one usage of each
REM      socket address is normally permitted" error.
REM   3. Removes the fixed `oms360_network` if it still exists and is no
REM      longer in use by any container (best-effort; if it's still
REM      attached to something, `docker network rm` fails harmlessly and
REM      that's fine - the next `docker compose up` will reuse it).
REM
REM Every command here is intentionally scoped to OMS360's own fixed
REM container names / network name / compose file - this never runs a
REM machine-wide `docker stop $(docker ps -q)` or `docker network prune`,
REM which DEC-0023 point 8 already identified and fixed as a real hazard to
REM any other Docker project on the machine.
REM
REM Failures here are logged as warnings, never fatal - an empty/fresh
REM environment (nothing to clean up) is the normal case on a first run,
REM and every command below is wrapped so a "nothing to remove" result
REM does not abort the script.
REM -----------------------------------------------------------------------
:cleanup_previous_environment
echo   Removing any previous OMS360 stack - docker compose down --remove-orphans...
call :write_log logs\startup.log "cleanup: docker compose down --remove-orphans"
docker compose -f %COMPOSE_FILE% down --remove-orphans >nul 2>&1

echo   Checking for leftover OMS360 containers by fixed name...
for %%C in (%MYSQL_CONTAINER% %ZOOKEEPER_CONTAINER% %KAFKA_CONTAINER% %ENGINE_CONTAINER% %CONSUMER_CONTAINER%) do (
    docker inspect %%C >nul 2>&1
    if not errorlevel 1 (
        echo     Found leftover container %%C - removing...
        call :write_log logs\startup.log "cleanup: force-removing leftover container %%C"
        docker rm -f %%C >nul 2>&1
    )
)

echo   Checking for an unused OMS360 network...
docker network inspect %NETWORK_NAME% >nul 2>&1
if not errorlevel 1 (
    docker network rm %NETWORK_NAME% >nul 2>&1
    if not errorlevel 1 (
        echo     Removed unused network %NETWORK_NAME%.
        call :write_log logs\startup.log "cleanup: removed unused network %NETWORK_NAME%"
    )
)
exit /b 0

REM -----------------------------------------------------------------------
REM :find_pid_on_port <port>
REM Added 2026-07-28 (see DEC-0042). Sets PORT_PID to the PID of whatever
REM process has a LISTENING socket on localhost:<port>, or leaves it
REM undefined if the port is free. Pure netstat/findstr - no PowerShell,
REM no parentheses inside the backquoted command, so this cannot hit the
REM cmd.exe FOR /F paren-parsing crash documented on :check_port above.
REM -----------------------------------------------------------------------
:find_pid_on_port
set "FPP_PORT=%~1"
set "PORT_PID="
for /f "usebackq tokens=5" %%P in (`netstat -ano ^| findstr /C:":%FPP_PORT% " ^| findstr /I LISTENING`) do set "PORT_PID=%%P"
exit /b 0

REM -----------------------------------------------------------------------
REM :get_process_name <pid>
REM Added 2026-07-28 (see DEC-0042). Sets PROC_NAME to the image name of
REM the given PID (e.g. mysqld.exe), or UNKNOWN if it can no longer be
REM resolved (process exited between the netstat snapshot and this call).
REM -----------------------------------------------------------------------
:get_process_name
set "GPN_PID=%~1"
set "PROC_NAME=UNKNOWN"
for /f "usebackq tokens=1 delims=," %%N in (`tasklist /FI "PID eq %GPN_PID%" /FO CSV /NH 2^>nul`) do set "PROC_NAME=%%~N"
exit /b 0

REM -----------------------------------------------------------------------
REM :free_port <port> <friendly-label>
REM Added 2026-07-28 (see DEC-0042). Requirement: "If a required port is
REM occupied, identify the owning process, display it, then terminate it
REM automatically."
REM
REM   1. Looks up whatever PID is LISTENING on <port>. If none, reports
REM      [OK] and returns immediately - nothing to do.
REM   2. PID 0 means the port is in the OS's own reserved/excluded range
REM      (common with Hyper-V/WSL2 dynamic port reservations) - this is
REM      not a real process, cannot be terminated, so it's reported as a
REM      warning and skipped rather than attempting (and failing) a kill.
REM   3. Otherwise resolves and PRINTS the owning process name before
REM      doing anything else, per the explicit requirement. If that name
REM      looks like a Docker Desktop component (docker*/vmmem), an extra
REM      caution line is printed, since terminating it can briefly disrupt
REM      Docker Desktop itself - it is still terminated, since that is
REM      what was asked for, but the operator is told why this might
REM      recur.
REM   4. Terminates it with `taskkill /F /PID`, waits briefly for the OS to
REM      release the socket, then re-checks the port. Failure to terminate
REM      (e.g. a protected process, or insufficient privileges) is
REM      reported as a warning, not a fatal script error - the actual
REM      `docker compose up` a few steps later is the authoritative check,
REM      and will fail loudly with Docker's own error if the port is truly
REM      still unavailable.
REM -----------------------------------------------------------------------
:free_port
set "FP_PORT=%~1"
set "FP_LABEL=%~2"
call :find_pid_on_port %FP_PORT%
if not defined PORT_PID (
    echo   [OK] Port %FP_PORT% - %FP_LABEL% - is free.
    exit /b 0
)
if "%PORT_PID%"=="0" (
    echo   [WARN] Port %FP_PORT% - %FP_LABEL% - shows PID 0, an OS-reserved port range. Cannot terminate - skipping.
    call :write_log logs\startup.log "port %FP_PORT% - %FP_LABEL% - reserved by OS (PID 0), skipped"
    exit /b 0
)
call :get_process_name %PORT_PID%
echo   [WARN] Port %FP_PORT% - %FP_LABEL% - is occupied by PID %PORT_PID% - process: %PROC_NAME%
echo %PROC_NAME%| findstr /I "docker vmmem" >nul
if not errorlevel 1 (
    echo   [CAUTION] %PROC_NAME% looks like a Docker Desktop component. Terminating
    echo             it may briefly disrupt Docker Desktop itself. If this keeps
    echo             recurring, try restarting Docker Desktop manually instead.
)
call :write_log logs\startup.log "port %FP_PORT% - %FP_LABEL% - occupied by PID %PORT_PID% (%PROC_NAME%) - terminating"
echo          Terminating PID %PORT_PID%...
taskkill /F /PID %PORT_PID% >nul 2>&1
ping -n 3 127.0.0.1 >nul
call :find_pid_on_port %FP_PORT%
if not defined PORT_PID (
    echo   [OK] Port %FP_PORT% - %FP_LABEL% - is now free.
    call :write_log logs\startup.log "port %FP_PORT% - %FP_LABEL% - freed successfully"
) else (
    echo   [WARN] Port %FP_PORT% - %FP_LABEL% - is still occupied after termination attempt.
    echo          This may be a Windows service that auto-restarts, or the process
    echo          may require Administrator privileges to terminate.
    call :write_log logs\startup.log "WARNING: port %FP_PORT% - %FP_LABEL% - still occupied after taskkill attempt"
)
exit /b 0
