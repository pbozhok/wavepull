@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."

netstat -ano | findstr "LISTENING" | findstr ":8000" >nul 2>&1
if %errorlevel% neq 0 (
    start "WavePull Server" /d "%PROJECT_ROOT%" /min cmd /k ".venv\Scripts\uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
    timeout /t 2 /nobreak >nul
)

start "" http://localhost:8000
endlocal
