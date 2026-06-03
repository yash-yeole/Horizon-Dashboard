@echo off
REM ============================================================
REM  HORIZON Energy Terminal - stop launcher
REM  Frees the dev ports by killing whatever listens on them.
REM  Targets ports only (not all python/node) to avoid
REM  killing unrelated processes.
REM ============================================================

setlocal enabledelayedexpansion
set "PORTS=8000 5173 5174"

echo Stopping HORIZON Energy Terminal servers...
echo.

for %%P in (%PORTS%) do (
    set "FOUND="
    for /f "tokens=5" %%I in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do (
        set "FOUND=1"
        echo   Port %%P  -> killing PID %%I
        taskkill /F /PID %%I >nul 2>&1
    )
    if not defined FOUND echo   Port %%P  -> nothing listening
)

echo.
echo Done. Ports 8000 / 5173 / 5174 are now free.
echo (This window will close in 3 seconds.)
timeout /t 3 >nul
