@echo off
REM ============================================================================
REM Smart Tire Analyzer - FULL PROJECT LAUNCHER
REM ============================================================================
REM One-click launcher for every deployment mode:
REM   [1] Local Dev   - Python venv + Next.js dev servers in separate windows
REM   [2] Docker       - Full containerized stack (Backend + Frontend + Redis + Nginx)
REM   [3] Docker Dev   - Backend only in Docker, Frontend runs locally (fast rebuild)
REM   [4] Kubernetes   - Deploy to local K8s cluster (Docker Desktop K8s)
REM   [5] Health Check - Verify all services are responding
REM   [6] Stop All     - Stop all running containers / K8s resources
REM   [7] Exit
REM ============================================================================

setlocal enabledelayedexpansion

set "REPO_ROOT=%~dp0"
if "%REPO_ROOT:~-1%"=="\" set "REPO_ROOT=%REPO_ROOT:~0,-1%"

set "VENV_DIR=%REPO_ROOT%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"
set "BACKEND_DIR=%REPO_ROOT%\backend"
set "FRONTEND_DIR=%REPO_ROOT%\frontend"
set "COMPOSE_FILE=%REPO_ROOT%\deployment\docker\docker-compose.yml"
set "K8S_DIR=%REPO_ROOT%\deployment\kubernetes"
set "K8S_NS=smart-tire"

:MENU
cls
echo.
echo  ============================================================
echo            SMART TIRE ANALYZER - PROJECT LAUNCHER
echo  ============================================================
echo.
echo   [1]  Local Development     (Python + Next.js on host)
echo   [2]  Docker Full Stack     (Backend + Frontend + Redis + Nginx)
echo   [3]  Docker Backend Only   (Backend in container, FE local)
echo   [4]  Kubernetes Deploy     (Deploy to local K8s cluster)
echo   [5]  Health Check          (Test all running services)
echo   [6]  Stop All              (Kill containers + K8s resources)
echo   [7]  Exit
echo.
echo  ============================================================
echo.
set /p "choice=  Select option (1-7): "

if "%choice%"=="1" goto LOCAL
if "%choice%"=="2" goto DOCKER_FULL
if "%choice%"=="3" goto DOCKER_BACKEND
if "%choice%"=="4" goto KUBERNETES
if "%choice%"=="5" goto HEALTH
if "%choice%"=="6" goto STOP
if "%choice%"=="7" exit /b 0
echo.
echo  [!] Invalid option. Press any key to try again...
pause >nul
goto MENU

REM ============================================================================
REM 1. LOCAL DEVELOPMENT
REM ============================================================================
:LOCAL
cls
echo.
echo  [1/4] Checking Python virtual environment...
if not exist "%VENV_PY%" (
    echo  [*] Virtual environment not found. Creating one...
    python -m venv "%VENV_DIR%"
    if !ERRORLEVEL! NEQ 0 (
        echo  [ERROR] Failed to create virtualenv. Is Python installed and in PATH?
        pause
        goto MENU
    )
    echo  [OK] Virtual environment created.
) else (
    echo  [OK] Virtual environment found.
)

echo.
echo  [2/4] Installing/updating Python backend dependencies...
"%VENV_PIP%" install -q -r "%BACKEND_DIR%\requirements.txt" 2>nul
if !ERRORLEVEL! NEQ 0 (
    echo  [WARN] Some Python packages may have failed. Continuing anyway...
) else (
    echo  [OK] Python dependencies ready.
)

echo.
echo  [3/4] Installing/updating Frontend (Next.js) dependencies...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo  [*] node_modules not found. Running npm install...
    npm --prefix "%FRONTEND_DIR%" install --no-audit --no-fund
) else (
    echo  [OK] Frontend dependencies already installed.
)

echo.
echo  [4/4] Setting up environment file...
if not exist "%REPO_ROOT%\.env" (
    if exist "%REPO_ROOT%\.env.example" (
        copy /Y "%REPO_ROOT%\.env.example" "%REPO_ROOT%\.env" >nul
        echo  [OK] Created .env from .env.example - add your API keys.
    ) else (
        echo  [WARN] No .env.example found. Create .env manually if needed.
    )
) else (
    echo  [OK] .env file exists.
)

echo.
echo  ------------------------------------------------------------
echo   Starting Backend (FastAPI) on http://127.0.0.1:8000 ...
echo  ------------------------------------------------------------
start "SmartTire-Backend" cmd /k "title Smart Tire - Backend && echo. && echo  Backend running at http://127.0.0.1:8000 && echo  API docs at http://127.0.0.1:8000/docs && echo. && set PYTHONPATH=%REPO_ROOT%;%BACKEND_DIR% && cd /d "%BACKEND_DIR%" && "%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo  ------------------------------------------------------------
echo   Starting Frontend (Next.js) on http://127.0.0.1:3000 ...
echo  ------------------------------------------------------------
start "SmartTire-Frontend" cmd /k "title Smart Tire - Frontend && echo. && echo  Frontend running at http://127.0.0.1:3000 && echo. && cd /d "%FRONTEND_DIR%" && npm run dev"

echo.
echo  ============================================================
echo   Services are starting in separate windows:
echo     Backend:  http://127.0.0.1:8000  (API docs: /docs)
echo     Frontend: http://127.0.0.1:3000
echo  ============================================================
echo.
pause
goto MENU

REM ============================================================================
REM 2. DOCKER FULL STACK
REM ============================================================================
:DOCKER_FULL
cls
echo.
echo  [1/3] Checking Docker Desktop...
docker info >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo  [ERROR] Docker Desktop is not running!
    echo  Please start Docker Desktop and try again.
    pause
    goto MENU
)
echo  [OK] Docker Desktop is running.

echo.
echo  [2/3] Setting up environment file...
if not exist "%REPO_ROOT%\.env" (
    if exist "%REPO_ROOT%\.env.example" (
        copy /Y "%REPO_ROOT%\.env.example" "%REPO_ROOT%\.env" >nul
        echo  [OK] Created .env from .env.example.
    )
)

echo.
echo  [3/3] Building and starting full stack...
echo  [*] This may take several minutes on first run...
echo.
cd /d "%REPO_ROOT%"
docker compose -f "%COMPOSE_FILE%" up --build -d
if !ERRORLEVEL! EQU 0 (
    echo.
    echo  ============================================================
    echo   Docker stack deployed successfully!
    echo     Backend:   http://localhost:8000  (API docs: /docs)
    echo     Frontend:  http://localhost:8081
    echo     Nginx:     http://localhost:80
    echo     Redis:     localhost:6379
    echo  ============================================================
) else (
    echo.
    echo  [ERROR] Docker Compose failed. Check Docker Desktop logs.
)
echo.
pause
goto MENU

REM ============================================================================
REM 3. DOCKER BACKEND ONLY
REM ============================================================================
:DOCKER_BACKEND
cls
echo.
echo  [1/2] Checking Docker Desktop...
docker info >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo  [ERROR] Docker Desktop is not running!
    pause
    goto MENU
)
echo  [OK] Docker Desktop is running.

echo.
echo  [2/2] Starting backend container only...
echo  [*] Frontend will run locally for fast iteration.
echo.

docker stop smart-tire-backend >nul 2>&1
docker rm smart-tire-backend >nul 2>&1

cd /d "%REPO_ROOT%"
docker compose -f "%COMPOSE_FILE%" up --build -d backend redis
if !ERRORLEVEL! EQU 0 (
    echo  [OK] Backend container started on http://localhost:8000
    echo.
    echo  Starting local frontend...
    start "SmartTire-Frontend" cmd /k "title Smart Tire - Frontend and Backend in Docker && echo. && echo  Frontend: http://127.0.0.1:3000 && echo  Backend:  http://localhost:8000 (Docker) && echo. && cd /d "%FRONTEND_DIR%" && npm run dev"
) else (
    echo  [ERROR] Failed to start backend container.
)
echo.
pause
goto MENU

REM ============================================================================
REM 4. KUBERNETES DEPLOYMENT
REM ============================================================================
:KUBERNETES
cls
echo.
echo  ============================================================
echo   KUBERNETES DEPLOYMENT
echo  ============================================================
echo.

echo  [1/5] Checking kubectl...
kubectl version --client >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo  [ERROR] kubectl is not installed or not in PATH.
    echo  Install via: winget install Kubernetes.kubectl
    pause
    goto MENU
)
echo  [OK] kubectl found.

echo.
echo  [2/5] Checking Kubernetes cluster connection...
kubectl cluster-info >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo  [ERROR] Cannot connect to a Kubernetes cluster.
    echo  Enable Kubernetes in Docker Desktop settings, then retry.
    pause
    goto MENU
)
echo  [OK] Connected to K8s cluster.

echo.
echo  [3/5] Applying namespace and manifests...
cd /d "%K8S_DIR%"
kubectl apply -f "%K8S_DIR%\service.yaml" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo  [ERROR] Failed to apply service.yaml
    pause
    goto MENU
)
kubectl apply -f "%K8S_DIR%\deployment.yaml" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo  [ERROR] Failed to apply deployment.yaml
    pause
    goto MENU
)
kubectl apply -f "%K8S_DIR%\hpa.yaml" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo  [WARN] Failed to apply hpa.yaml (non-fatal, HPA optional)
)
echo  [OK] Manifests applied.

echo.
echo  [4/5] Waiting for rollout to complete...
echo  [*] This may take a few minutes on first deploy...
kubectl -n %K8S_NS% rollout status deployment/smart-tire-backend --timeout=300s
if !ERRORLEVEL! NEQ 0 (
    echo  [WARN] Rollout timed out. Pods may still be starting.
)

echo.
echo  [5/5] Retrieving service endpoint...
kubectl -n %K8S_NS% get svc smart-tire-backend-svc -o wide
echo.
echo  To access the API via port-forward, run:
echo    kubectl -n %K8S_NS% port-forward svc/smart-tire-backend-svc 8000:80
echo  Then open: http://localhost:8000/docs
echo.
echo  ============================================================
echo   K8s deployment complete!
echo  ============================================================
echo.
pause
goto MENU

REM ============================================================================
REM 5. HEALTH CHECK
REM ============================================================================
:HEALTH
cls
echo.
echo  ============================================================
echo   SERVICE HEALTH CHECK
echo  ============================================================
echo.

echo  [1] Backend API (http://localhost:8000/health)...
curl -s -o nul -w "    Status: %%{http_code}\n" http://localhost:8000/health 2>nul
if !ERRORLEVEL! NEQ 0 echo    Status: UNREACHABLE

echo.
echo  [2] Frontend (http://localhost:3000)...
curl -s -o nul -w "    Status: %%{http_code}\n" http://localhost:3000 2>nul
if !ERRORLEVEL! NEQ 0 echo    Status: UNREACHABLE

echo.
echo  [3] Nginx (http://localhost:80)...
curl -s -o nul -w "    Status: %%{http_code}\n" http://localhost:80 2>nul
if !ERRORLEVEL! NEQ 0 echo    Status: UNREACHABLE

echo.
echo  [4] Kubernetes pods (if deployed)...
kubectl -n %K8S_NS% get pods -o wide 2>nul
if !ERRORLEVEL! NEQ 0 echo    K8s: kubectl not available or cluster not running

echo.
echo  ============================================================
echo.
pause
goto MENU

REM ============================================================================
REM 6. STOP ALL
REM ============================================================================
:STOP
cls
echo.
echo  ============================================================
echo   STOPPING ALL SERVICES
echo  ============================================================
echo.

echo  [1/3] Stopping Docker Compose stack...
cd /d "%REPO_ROOT%"
docker compose -f "%COMPOSE_FILE%" down 2>nul
if !ERRORLEVEL! EQU 0 (
    echo  [OK] Docker Compose stack stopped.
) else (
    echo  [WARN] docker-compose down failed (stack may not be running).
)

echo.
echo  [2/3] Removing stray containers...
docker stop smart-tire-backend >nul 2>&1
docker rm smart-tire-backend >nul 2>&1
echo  [OK] Stray containers cleaned.

echo.
echo  [3/3] Deleting Kubernetes resources...
kubectl -n %K8S_NS% delete hpa smart-tire-hpa --ignore-not-found 2>nul
kubectl -n %K8S_NS% delete svc smart-tire-backend-svc --ignore-not-found 2>nul
kubectl -n %K8S_NS% delete deployment smart-tire-backend --ignore-not-found 2>nul
kubectl -n %K8S_NS% delete pvc smart-tire-model-pvc --ignore-not-found 2>nul
kubectl delete namespace %K8S_NS% --ignore-not-found 2>nul
echo  [OK] K8s resources deleted.

echo.
echo  ============================================================
echo   All services stopped.
echo  ============================================================
echo.
pause
goto MENU
