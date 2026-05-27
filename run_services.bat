@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================
rem   Smart Tire Analyzer - Local + Docker Launcher
rem
rem   Common commands:
rem     run_services.bat              Start local backend + frontend
rem     run_services.bat start        Start local backend + frontend
rem     run_services.bat restart      Restart local backend + frontend
rem     run_services.bat stop         Stop local backend + frontend
rem     run_services.bat status       Show local service status
rem     run_services.bat logs         Follow local logs
rem
rem   Docker commands:
rem     run_services.bat docker
rem     run_services.bat docker-restart
rem     run_services.bat docker-stop
rem     run_services.bat docker-status
rem     run_services.bat docker-logs
rem
rem   Optional environment overrides:
rem     SMART_TIRE_BACKEND_PORT=8000
rem     SMART_TIRE_FRONTEND_PORT=3000
rem     SMART_TIRE_OPEN_BROWSER=1
rem     SMART_TIRE_NO_PAUSE=1
rem ============================================================

set "ROOT=%~dp0"
set "ROOT=!ROOT:~0,-1!"
set "COMPOSE_FILE=!ROOT!\deployment\docker\docker-compose.yml"
set "DOCKER_BACKEND_URL=http://localhost:8000"
set "DOCKER_FRONTEND_URL=http://localhost:8081"

if not defined SMART_TIRE_BACKEND_PORT set "SMART_TIRE_BACKEND_PORT=8000"
if not defined SMART_TIRE_FRONTEND_PORT set "SMART_TIRE_FRONTEND_PORT=3000"
if not defined SMART_TIRE_OPEN_BROWSER set "SMART_TIRE_OPEN_BROWSER=1"

set "LOCAL_BACKEND_HOST=127.0.0.1"
set "LOCAL_FRONTEND_HOST=127.0.0.1"
set "LOCAL_BACKEND_URL=http://!LOCAL_BACKEND_HOST!:!SMART_TIRE_BACKEND_PORT!"
set "LOCAL_FRONTEND_URL=http://!LOCAL_FRONTEND_HOST!:!SMART_TIRE_FRONTEND_PORT!"
set "BACKEND_OUT_LOG=!ROOT!\logs\backend-local.out.log"
set "BACKEND_ERR_LOG=!ROOT!\logs\backend-local.err.log"
set "FRONTEND_OUT_LOG=!ROOT!\logs\frontend-local.out.log"
set "FRONTEND_ERR_LOG=!ROOT!\logs\frontend-local.err.log"

cd /d "!ROOT!" || goto fail

set "ACTION=%~1"
if "!ACTION!"=="" set "ACTION=local"
if /i "!ACTION!"=="start" set "ACTION=local"

if /i "!ACTION!"=="local" goto start_local
if /i "!ACTION!"=="restart" goto restart_local
if /i "!ACTION!"=="stop" goto stop_local
if /i "!ACTION!"=="status" goto status_local
if /i "!ACTION!"=="logs" goto logs_local

if /i "!ACTION!"=="docker" goto start_docker
if /i "!ACTION!"=="docker-restart" goto restart_docker
if /i "!ACTION!"=="docker-stop" goto stop_docker
if /i "!ACTION!"=="docker-status" goto status_docker
if /i "!ACTION!"=="docker-logs" goto logs_docker

if /i "!ACTION!"=="help" goto help
if /i "!ACTION!"=="--help" goto help
if /i "!ACTION!"=="-h" goto help

echo Unknown command: !ACTION!
goto help

:start_local
cls
echo ============================================================
echo    Smart Tire Analyzer ^| Local Development
echo ============================================================
echo    Project : !ROOT!
echo    Backend : !LOCAL_BACKEND_URL!
echo    Frontend: !LOCAL_FRONTEND_URL!
echo.

call :ensure_env
call :ensure_dirs
call :ensure_python || goto fail
call :ensure_backend_deps || goto fail
call :ensure_frontend_deps || goto fail
call :warn_missing_model

set "PYTHONPATH=!ROOT!;!ROOT!\backend;!PYTHONPATH!"
set "NEXT_PUBLIC_API_BASE_URL=!LOCAL_BACKEND_URL!"

call :is_url_ready "!LOCAL_BACKEND_URL!/health"
if errorlevel 1 (
    call :ensure_port_available "!SMART_TIRE_BACKEND_PORT!" "Backend" || goto fail
    echo    Starting backend...
    call :start_backend || goto fail
) else (
    echo    Backend already responds at !LOCAL_BACKEND_URL!.
)

echo.
echo    Waiting for backend startup...
call :wait_for_url "!LOCAL_BACKEND_URL!/health" "Backend API" 90
if errorlevel 1 (
    call :print_local_log_tail
    goto fail
)
call :warn_backend_readiness "!LOCAL_BACKEND_URL!" "Backend API"

call :is_url_ready "!LOCAL_FRONTEND_URL!"
if errorlevel 1 (
    call :ensure_port_available "!SMART_TIRE_FRONTEND_PORT!" "Frontend" || goto fail
    echo.
    echo    Starting frontend...
    call :start_frontend || goto fail
) else (
    echo    Frontend already responds at !LOCAL_FRONTEND_URL!.
)

echo.
echo    Waiting for frontend startup...
call :wait_for_url "!LOCAL_FRONTEND_URL!" "Frontend Web" 90
if errorlevel 1 (
    call :print_local_log_tail
    goto fail
)

echo.
echo    Reading backend health...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$base='!LOCAL_BACKEND_URL!';" ^
  "try { $h=Invoke-RestMethod ($base + '/health') -TimeoutSec 8; Write-Host ('   status : ' + $h.status); Write-Host ('   model  : ' + $h.components.model); Write-Host ('   version: ' + $h.components.model_version) }" ^
  "catch { Write-Host '   WARNING: Could not read backend health summary.' }"

echo.
echo ============================================================
echo    Local services are running.
echo.
echo    Frontend    : !LOCAL_FRONTEND_URL!
echo    Dashboard   : !LOCAL_FRONTEND_URL!/dashboard
echo    Backend API : !LOCAL_BACKEND_URL!
echo    API Docs    : !LOCAL_BACKEND_URL!/docs
echo.
echo    Useful commands:
echo      run_services.bat status
echo      run_services.bat logs
echo      run_services.bat stop
echo ============================================================

call :should_open_browser
if not errorlevel 1 (
    start "" "!LOCAL_FRONTEND_URL!"
    start "" "!LOCAL_BACKEND_URL!/docs"
)
goto done

:restart_local
call :stop_local_no_pause
goto start_local

:stop_local
call :stop_local_no_pause
goto done

:stop_local_no_pause
echo.
echo    Stopping local Smart Tire Analyzer processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root='!ROOT!';" ^
  "$ports=@([int]'!SMART_TIRE_BACKEND_PORT!',[int]'!SMART_TIRE_FRONTEND_PORT!');" ^
  "$portPids=@(Get-NetTCPConnection -LocalPort $ports -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique);" ^
  "$all=@(Get-CimInstance Win32_Process); $byId=@{}; $all | ForEach-Object { $byId[[int]$_.ProcessId]=$_ };" ^
  "function Test-ProjectProc($proc){ $seen=@{}; $cur=$proc; while($cur -and -not $seen.ContainsKey([int]$cur.ProcessId)){ $seen[[int]$cur.ProcessId]=$true; if($cur.CommandLine -and $cur.CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0){ return $true }; if(-not $cur.ParentProcessId -or -not $byId.ContainsKey([int]$cur.ParentProcessId)){ break }; $cur=$byId[[int]$cur.ParentProcessId] }; return $false };" ^
  "$procs=$all | Where-Object { (Test-ProjectProc $_) -and (($_.CommandLine -match 'uvicorn') -or ($_.CommandLine -match 'next') -or ($_.CommandLine -match 'npm') -or ($portPids -contains $_.ProcessId)) };" ^
  "if (-not $procs) { Write-Host '   No matching local processes found.'; exit 0 };" ^
  "$procs | Sort-Object ProcessId -Unique | ForEach-Object { Write-Host ('   Stopping PID ' + $_.ProcessId + ': ' + $_.Name); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
exit /b 0

:status_local
echo.
echo    Local service status
echo    --------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$backend='!LOCAL_BACKEND_URL!'; $frontend='!LOCAL_FRONTEND_URL!'; $ports=@([int]'!SMART_TIRE_BACKEND_PORT!',[int]'!SMART_TIRE_FRONTEND_PORT!'); $root='!ROOT!';" ^
  "try { $h=Invoke-RestMethod ($backend + '/health') -TimeoutSec 5; Write-Host ('Backend : alive / ' + $h.status) } catch { Write-Host 'Backend : not reachable' };" ^
  "try { $r=Invoke-RestMethod ($backend + '/health/ready') -TimeoutSec 5; Write-Host ('Ready   : ' + $r.status + ' / model=' + $r.components.model + ' / database=' + $r.components.database) } catch { Write-Host 'Ready   : not ready or not reachable' };" ^
  "try { $web=Invoke-WebRequest $frontend -UseBasicParsing -TimeoutSec 5; Write-Host ('Frontend: HTTP ' + $web.StatusCode) } catch { Write-Host 'Frontend: not reachable' };" ^
  "Write-Host ''; Write-Host 'Listening ports:';" ^
  "$all=@(Get-CimInstance Win32_Process); $byId=@{}; $all | ForEach-Object { $byId[[int]$_.ProcessId]=$_ };" ^
  "function Test-ProjectProc($proc){ $seen=@{}; $cur=$proc; while($cur -and -not $seen.ContainsKey([int]$cur.ProcessId)){ $seen[[int]$cur.ProcessId]=$true; if($cur.CommandLine -and $cur.CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0){ return $true }; if(-not $cur.ParentProcessId -or -not $byId.ContainsKey([int]$cur.ParentProcessId)){ break }; $cur=$byId[[int]$cur.ParentProcessId] }; return $false };" ^
  "$rows=@(); Get-NetTCPConnection -LocalPort $ports -State Listen -ErrorAction SilentlyContinue | ForEach-Object { $proc=$byId[[int]$_.OwningProcess]; $rows += [pscustomobject]@{ LocalAddress=$_.LocalAddress; LocalPort=$_.LocalPort; PID=$_.OwningProcess; Process=if($proc){$proc.Name}else{'unknown'}; Project=if($proc -and (Test-ProjectProc $proc)){'yes'}else{'no'} } };" ^
  "if($rows.Count){ $rows | Format-Table -AutoSize } else { Write-Host '   none' }"
goto done

:logs_local
echo.
echo    Following local logs. Press Ctrl+C to stop watching.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$files=@('!BACKEND_ERR_LOG!','!BACKEND_OUT_LOG!','!FRONTEND_ERR_LOG!','!FRONTEND_OUT_LOG!') | Where-Object { Test-Path $_ };" ^
  "if (-not $files) { Write-Host 'No local log files found yet.'; exit 0 };" ^
  "Write-Host 'Watching:'; $files | ForEach-Object { Write-Host ('  ' + $_) };" ^
  "Get-Content -Path $files -Tail 80 -Wait"
goto done

:start_docker
cls
echo ============================================================
echo    Smart Tire Analyzer ^| Docker Deployment
echo ============================================================
echo    Project : !ROOT!
echo    Backend : !DOCKER_BACKEND_URL!
echo    Frontend: !DOCKER_FRONTEND_URL!
echo.

call :check_compose_file || goto fail
call :ensure_docker_engine || goto fail
call :ensure_env
call :ensure_dirs
call :warn_missing_model

echo.
echo    Building and starting Docker containers...
docker compose --project-directory "!ROOT!" -f "!COMPOSE_FILE!" up -d --build backend frontend
if errorlevel 1 goto fail

echo.
echo    Waiting for backend startup...
call :wait_for_url "!DOCKER_BACKEND_URL!/health" "Docker Backend API" 120 || goto fail
call :warn_backend_readiness "!DOCKER_BACKEND_URL!" "Docker Backend API"

echo.
echo    Waiting for frontend startup...
call :wait_for_url "!DOCKER_FRONTEND_URL!" "Docker Frontend Web" 90 || goto fail

echo.
echo ============================================================
echo    Docker services are running.
echo.
echo    Frontend    : !DOCKER_FRONTEND_URL!
echo    Dashboard   : !DOCKER_FRONTEND_URL!/dashboard
echo    Backend API : !DOCKER_BACKEND_URL!
echo    API Docs    : !DOCKER_BACKEND_URL!/docs
echo ============================================================

call :should_open_browser
if not errorlevel 1 (
    start "" "!DOCKER_FRONTEND_URL!"
    start "" "!DOCKER_BACKEND_URL!/docs"
)
goto done

:restart_docker
call :check_compose_file || goto fail
call :ensure_docker_engine || goto fail
docker compose --project-directory "!ROOT!" -f "!COMPOSE_FILE!" down
if errorlevel 1 goto fail
goto start_docker

:stop_docker
call :check_compose_file || goto fail
call :ensure_docker_engine || goto fail
echo.
echo    Stopping Docker containers...
docker compose --project-directory "!ROOT!" -f "!COMPOSE_FILE!" down
if errorlevel 1 goto fail
goto done

:status_docker
call :check_compose_file || goto fail
call :ensure_docker_engine || goto fail
docker compose --project-directory "!ROOT!" -f "!COMPOSE_FILE!" ps
goto done

:logs_docker
call :check_compose_file || goto fail
call :ensure_docker_engine || goto fail
docker compose --project-directory "!ROOT!" -f "!COMPOSE_FILE!" logs -f backend frontend
goto done

:help
echo.
echo Smart Tire Analyzer launcher
echo.
echo   run_services.bat                 Start local backend + frontend
echo   run_services.bat start           Start local backend + frontend
echo   run_services.bat restart         Restart local services
echo   run_services.bat stop            Stop local services
echo   run_services.bat status          Check local services
echo   run_services.bat logs            Follow local logs
echo.
echo   run_services.bat docker          Build/start Docker services
echo   run_services.bat docker-restart  Restart Docker services
echo   run_services.bat docker-stop     Stop Docker services
echo   run_services.bat docker-status   Check Docker services
echo   run_services.bat docker-logs     Follow Docker logs
echo.
echo Environment overrides:
echo   SMART_TIRE_BACKEND_PORT          Backend port, default 8000
echo   SMART_TIRE_FRONTEND_PORT         Frontend port, default 3000
echo   SMART_TIRE_OPEN_BROWSER          1 opens browser, 0 disables it
echo   SMART_TIRE_NO_PAUSE              1 disables final pause
goto done

:ensure_python
if exist "!ROOT!\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=!ROOT!\.venv\Scripts\python.exe"
    exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
    echo    ERROR: Python was not found. Install Python 3.10+ and run this again.
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo    ERROR: Python 3.10 or newer is required.
    exit /b 1
)

echo    Creating Python virtual environment...
python -m venv "!ROOT!\.venv"
if errorlevel 1 (
    echo    ERROR: Could not create .venv.
    exit /b 1
)
set "PYTHON_EXE=!ROOT!\.venv\Scripts\python.exe"
exit /b 0

:ensure_backend_deps
set "BACKEND_DEPS_MARKER=!ROOT!\.venv\.backend-deps.stamp"
set "NEED_BACKEND_DEPS=0"

"!PYTHON_EXE!" -c "import fastapi, uvicorn, torch, torchvision, cv2, sqlalchemy" >nul 2>nul
if errorlevel 1 set "NEED_BACKEND_DEPS=1"

if "!NEED_BACKEND_DEPS!"=="0" (
    if exist "!BACKEND_DEPS_MARKER!" (
        call :file_newer_than "!ROOT!\backend\requirements.txt" "!BACKEND_DEPS_MARKER!"
        if errorlevel 1 set "NEED_BACKEND_DEPS=1"
    ) else (
        powershell -NoProfile -ExecutionPolicy Bypass -Command "New-Item -ItemType File -Path '!BACKEND_DEPS_MARKER!' -Force | Out-Null"
    )
)

if not "!NEED_BACKEND_DEPS!"=="1" exit /b 0

echo    Installing backend Python dependencies...
"!PYTHON_EXE!" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"!PYTHON_EXE!" -m pip install -r "!ROOT!\backend\requirements.txt"
if errorlevel 1 (
    echo    ERROR: Backend dependency install failed.
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "New-Item -ItemType File -Path '!BACKEND_DEPS_MARKER!' -Force | Out-Null"
exit /b 0

:ensure_frontend_deps
where npm >nul 2>nul
if errorlevel 1 (
    echo    ERROR: npm was not found. Install Node.js, then run this again.
    exit /b 1
)
if not exist "!ROOT!\frontend\package.json" (
    echo    ERROR: Missing frontend package.json at !ROOT!\frontend\package.json
    exit /b 1
)

call :frontend_deps_stale
if not errorlevel 1 exit /b 0

echo    Installing frontend dependencies...
pushd "!ROOT!\frontend" >nul
call npm install
set "NPM_EXIT=!ERRORLEVEL!"
popd >nul
if not "!NPM_EXIT!"=="0" (
    echo    ERROR: Frontend dependency install failed.
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "New-Item -ItemType File -Path '!ROOT!\frontend\node_modules\.smart-tire-install.stamp' -Force | Out-Null"
exit /b 0

:frontend_deps_stale
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root='!ROOT!'; $marker=Join-Path $root 'frontend\node_modules\.smart-tire-install.stamp'; $nodeModules=Join-Path $root 'frontend\node_modules';" ^
  "if (-not (Test-Path $nodeModules)) { exit 1 };" ^
  "$required=@('next','react','react-dom') | ForEach-Object { Join-Path $nodeModules $_ };" ^
  "foreach($pkg in $required){ if(-not (Test-Path $pkg)){ exit 1 } };" ^
  "if (-not (Test-Path $marker)) { New-Item -ItemType File -Path $marker -Force | Out-Null; exit 0 };" ^
  "$markerTime=(Get-Item $marker).LastWriteTimeUtc;" ^
  "$files=@('frontend\package.json','frontend\package-lock.json') | ForEach-Object { Join-Path $root $_ } | Where-Object { Test-Path $_ };" ^
  "foreach($file in $files){ if((Get-Item $file).LastWriteTimeUtc -gt $markerTime){ exit 1 } };" ^
  "exit 0"
exit /b %ERRORLEVEL%

:file_newer_than
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$source='%~1'; $target='%~2';" ^
  "if (-not (Test-Path $target)) { exit 1 };" ^
  "if ((Get-Item $source).LastWriteTimeUtc -gt (Get-Item $target).LastWriteTimeUtc) { exit 1 };" ^
  "exit 0"
exit /b %ERRORLEVEL%

:start_backend
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$env:PYTHONPATH='!PYTHONPATH!';" ^
  "$env:PYTHONUNBUFFERED='1';" ^
  "Start-Process -FilePath '!PYTHON_EXE!' -ArgumentList @('-m','uvicorn','app.main:app','--app-dir','backend','--host','!LOCAL_BACKEND_HOST!','--port','!SMART_TIRE_BACKEND_PORT!') -WorkingDirectory '!ROOT!' -RedirectStandardOutput '!BACKEND_OUT_LOG!' -RedirectStandardError '!BACKEND_ERR_LOG!' -WindowStyle Hidden"
exit /b %ERRORLEVEL%

:start_frontend
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$env:NEXT_PUBLIC_API_BASE_URL='!LOCAL_BACKEND_URL!';" ^
  "Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue;" ^
  "Start-Process -FilePath 'npm.cmd' -ArgumentList @('run','dev','--','--hostname','!LOCAL_FRONTEND_HOST!','-p','!SMART_TIRE_FRONTEND_PORT!') -WorkingDirectory '!ROOT!\frontend' -RedirectStandardOutput '!FRONTEND_OUT_LOG!' -RedirectStandardError '!FRONTEND_ERR_LOG!' -WindowStyle Hidden"
exit /b %ERRORLEVEL%

:ensure_port_available
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$port=[int]'%~1'; $label='%~2'; $root='!ROOT!'; $blocked=$false;" ^
  "$listeners=Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue;" ^
  "if (-not $listeners) { exit 0 };" ^
  "$all=@(Get-CimInstance Win32_Process); $byId=@{}; $all | ForEach-Object { $byId[[int]$_.ProcessId]=$_ };" ^
  "function Test-ProjectProc($proc){ $seen=@{}; $cur=$proc; while($cur -and -not $seen.ContainsKey([int]$cur.ProcessId)){ $seen[[int]$cur.ProcessId]=$true; if($cur.CommandLine -and $cur.CommandLine.IndexOf($root,[StringComparison]::OrdinalIgnoreCase) -ge 0){ return $true }; if(-not $cur.ParentProcessId -or -not $byId.ContainsKey([int]$cur.ParentProcessId)){ break }; $cur=$byId[[int]$cur.ParentProcessId] }; return $false };" ^
  "foreach($conn in $listeners) { $owner=$conn.OwningProcess; $proc=$byId[[int]$owner]; $cmd=if($proc){$proc.CommandLine}else{''}; $isProject=$proc -and (Test-ProjectProc $proc); if($isProject){ Write-Host ('   ' + $label + ' port ' + $port + ' is already used by this project (PID ' + $owner + ').') } else { Write-Host ('   ERROR: ' + $label + ' port ' + $port + ' is already in use by PID ' + $owner + '.'); if($proc){ Write-Host ('   Process: ' + $proc.Name); if($cmd){ Write-Host ('   Command: ' + $cmd) } }; $blocked=$true } };" ^
  "if($blocked){ exit 1 } exit 0"
exit /b %ERRORLEVEL%

:check_compose_file
if not exist "!COMPOSE_FILE!" (
    echo    ERROR: Missing compose file: !COMPOSE_FILE!
    exit /b 1
)
exit /b 0

:check_docker_cli
where docker >nul 2>nul
if errorlevel 1 (
    echo    ERROR: Docker CLI was not found. Install Docker Desktop first.
    exit /b 1
)
docker compose version >nul 2>nul
if errorlevel 1 (
    echo    ERROR: Docker Compose v2 was not found. Update Docker Desktop first.
    exit /b 1
)
exit /b 0

:ensure_docker_engine
call :check_docker_cli || exit /b 1
docker info >nul 2>nul
if not errorlevel 1 exit /b 0

echo    Docker engine is not running. Starting Docker Desktop...
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
) else if exist "%LocalAppData%\Docker\Docker Desktop.exe" (
    start "" "%LocalAppData%\Docker\Docker Desktop.exe"
) else if exist "%LocalAppData%\Docker\Docker\Docker Desktop.exe" (
    start "" "%LocalAppData%\Docker\Docker\Docker Desktop.exe"
) else (
    echo    ERROR: Could not find Docker Desktop.
    exit /b 1
)

for /l %%i in (1,1,60) do (
    docker info >nul 2>nul
    if not errorlevel 1 (
        echo    Docker Desktop is ready.
        exit /b 0
    )
    echo    Waiting for Docker Desktop ... %%i/60
    timeout /t 3 /nobreak >nul
)

echo    ERROR: Docker Desktop did not become ready in time.
exit /b 1

:ensure_env
if not exist "!ROOT!\.env" (
    if exist "!ROOT!\.env.example" (
        copy "!ROOT!\.env.example" "!ROOT!\.env" >nul
        echo    Created .env from .env.example. Add API keys later if needed.
    ) else (
        echo    No .env file found. Optional API integrations will use fallback mode.
    )
)
exit /b 0

:ensure_dirs
if not exist "!ROOT!\continuous_learning\wrong_predictions" mkdir "!ROOT!\continuous_learning\wrong_predictions" >nul 2>nul
if not exist "!ROOT!\continuous_learning\user_feedback" mkdir "!ROOT!\continuous_learning\user_feedback" >nul 2>nul
if not exist "!ROOT!\continuous_learning\model_versions" mkdir "!ROOT!\continuous_learning\model_versions" >nul 2>nul
if not exist "!ROOT!\ai_model\saved_models" mkdir "!ROOT!\ai_model\saved_models" >nul 2>nul
if not exist "!ROOT!\logs" mkdir "!ROOT!\logs" >nul 2>nul
if not exist "!ROOT!\dataset\ocr_training_examples" mkdir "!ROOT!\dataset\ocr_training_examples" >nul 2>nul
exit /b 0

:warn_missing_model
if not exist "!ROOT!\ai_model\saved_models\hybrid_torch\model_best.pt" if not exist "!ROOT!\ai_model\saved_models\hybrid_torch\model_last.pt" (
    echo.
    echo    WARNING: Trained hybrid checkpoint was not found:
    echo    !ROOT!\ai_model\saved_models\hybrid_torch\model_best.pt
    echo    !ROOT!\ai_model\saved_models\hybrid_torch\model_last.pt
    echo    Backend can still start, but inference may use fallback behavior.
)
exit /b 0

:warn_backend_readiness
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$base='%~1'; $name='%~2';" ^
  "try { $r=Invoke-RestMethod ($base + '/health/ready') -TimeoutSec 8; Write-Host ('   ' + $name + ' readiness: ' + $r.status + ' / model=' + $r.components.model + ' / database=' + $r.components.database); exit 0 }" ^
  "catch { Write-Host ('   WARNING: ' + $name + ' is alive, but readiness is not fully ready.'); try { $h=Invoke-RestMethod ($base + '/health') -TimeoutSec 5; Write-Host ('   health status: ' + $h.status); Write-Host ('   model       : ' + $h.components.model) } catch {}; exit 0 }"
exit /b 0

:print_backend_health
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$base='%~1';" ^
  "try { $h=Invoke-RestMethod ($base + '/health') -TimeoutSec 8; Write-Host ('   status : ' + $h.status); Write-Host ('   model  : ' + $h.components.model); Write-Host ('   version: ' + $h.components.model_version) }" ^
  "catch { Write-Host '   WARNING: Could not read backend health summary.' }"
exit /b 0

:is_url_ready
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%~1' -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }"
exit /b %ERRORLEVEL%

:wait_for_url
set "WAIT_URL=%~1"
set "WAIT_NAME=%~2"
set "WAIT_ATTEMPTS=%~3"
for /l %%i in (1,1,!WAIT_ATTEMPTS!) do (
    call :is_url_ready "!WAIT_URL!"
    if not errorlevel 1 (
        echo    !WAIT_NAME! is ready.
        exit /b 0
    )
    echo    Waiting for !WAIT_NAME! ... %%i/!WAIT_ATTEMPTS!
    timeout /t 2 /nobreak >nul
)
echo    ERROR: !WAIT_NAME! did not become ready.
exit /b 1

:print_local_log_tail
echo.
echo    Recent local logs:
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$files=@('!BACKEND_ERR_LOG!','!BACKEND_OUT_LOG!','!FRONTEND_ERR_LOG!','!FRONTEND_OUT_LOG!') | Where-Object { Test-Path $_ };" ^
  "if (-not $files) { Write-Host '   No local log files found yet.'; exit 0 };" ^
  "foreach($file in $files){ Write-Host ''; Write-Host ('--- ' + $file + ' ---'); Get-Content -Path $file -Tail 40 -ErrorAction SilentlyContinue }"
exit /b 0

:should_open_browser
if /i "!SMART_TIRE_OPEN_BROWSER!"=="0" exit /b 1
if /i "!SMART_TIRE_OPEN_BROWSER!"=="false" exit /b 1
if /i "!SMART_TIRE_OPEN_BROWSER!"=="no" exit /b 1
if /i "!SMART_TIRE_OPEN_BROWSER!"=="off" exit /b 1
exit /b 0

:fail
echo.
echo ============================================================
echo    The launcher did not complete.
echo.
echo    Useful diagnostics:
echo      run_services.bat status
echo      run_services.bat logs
echo.
echo    Local log files:
echo      !BACKEND_ERR_LOG!
echo      !BACKEND_OUT_LOG!
echo      !FRONTEND_ERR_LOG!
echo      !FRONTEND_OUT_LOG!
echo ============================================================
if defined SMART_TIRE_NO_PAUSE (
    endlocal
    exit /b 1
)
pause
exit /b 1

:done
echo.
if defined SMART_TIRE_NO_PAUSE (
    endlocal
    exit /b 0
)
pause
endlocal
exit /b 0
