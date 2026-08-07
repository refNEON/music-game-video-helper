@echo off
setlocal

:: Switch to project directory first to avoid space issues in path
cd /d "C:\Users\lenovo\Desktop\music-game-video-helper-main\backend"

set CONDA_PYTHON=C:\Users\lenovo\anaconda3\envs\music_video_helper\python.exe

echo ==========================================
echo   SyncStage Dev Environment Startup
echo ==========================================
echo.
timeout /t 1 >nul

echo [1/3] Starting Redis Server...
start "Redis Server" cmd /k redis-server
timeout /t 2 >nul

echo [2/3] Starting Flask Backend...
start "Flask Backend" cmd /k %CONDA_PYTHON% app.py
timeout /t 3 >nul

echo [3/3] Starting Celery Worker...
start "Celery Worker" cmd /k %CONDA_PYTHON% -m celery -A task worker --loglevel=info --pool=solo
timeout /t 2 >nul

echo.
echo ==========================================
echo   All services started successfully!
echo ==========================================
echo.
echo   Frontend: Open frontend/cupnb.html directly
echo   API:      http://localhost:5000
echo   Health:   http://localhost:5000/health
echo.
pause
