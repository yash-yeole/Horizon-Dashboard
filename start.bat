@echo off
REM ============================================================
REM  HORIZON Energy Terminal - one-click dev launcher
REM  Opens two terminal windows: FastAPI backend + Vite frontend
REM ============================================================

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%energy-dashboard"
set "NODE_DIR=C:\Program Files\nodejs"

echo Starting HORIZON Energy Terminal...
echo   Backend  : http://localhost:8000  (docs at /docs)
echo   Frontend : http://localhost:5173
echo.

REM --- Backend: uses the venv's python directly (no activation needed) ---
if exist "%BACKEND%\.venv\Scripts\python.exe" (
    start "HORIZON Backend" cmd /k "cd /d "%BACKEND%" && ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000"
) else (
    echo [WARN] Backend venv not found at "%BACKEND%\.venv".
    echo        Create it first:  cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
)

REM --- Frontend: prepend Node to PATH for this window so npm is found ---
start "HORIZON Frontend" cmd /k "set "PATH=%NODE_DIR%;%PATH%" && cd /d "%FRONTEND%" && npm run dev"

echo Two terminal windows are launching.
echo Close those windows (or press Ctrl+C in each) to stop the servers.
echo This launcher window can now be closed.
