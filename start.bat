@echo off
TITLE IRIS — Indian Road Intelligence ^& Safe-Space Planner (Team KNIGHTS)
COLOR 0B

echo ==========================================================================
echo IRIS -- Indian Road Intelligence ^& Safe-Space Planner
echo Team: KNIGHTS ^| SIH26037
echo Tagline: "Predict the road before the road becomes dangerous."
echo ==========================================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python backend environment...
python -c "import fastapi, uvicorn, numpy, pygame; print('[OK] Python dependencies verified.')" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing required Python dependencies...
    pip install -r requirements.txt
)

echo [2/3] Checking frontend production build...
if not exist "frontend\dist\index.html" (
    echo [*] Building React + Vite + Tailwind frontend...
    cd frontend
    call npm.cmd install
    call npm.cmd run build
    cd ..
)

echo [3/3] Launching IRIS Central FastAPI Server ^& Web Dashboard...
start http://127.0.0.1:8000

echo.
echo ==========================================================================
echo [SUCCESS] IRIS Web Application is live at: http://127.0.0.1:8000
echo Press CTRL+C to terminate the server.
echo ==========================================================================
echo.

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
