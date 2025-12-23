@echo off
chcp 65001 > nul
echo ==========================================
echo   Intelligent Log Manager - Startup
echo ==========================================

echo [1/6] Checking Python dependencies...
python -c "import fastapi, elasticsearch, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo ❌ Python dependencies are missing!
    echo.
    echo Please install dependencies using one of these methods:
    echo 1. Run install_dependencies.py in PyCharm
    echo 2. Run in PyCharm terminal: pip install fastapi uvicorn elasticsearch
    echo 3. Use PyCharm Settings → Python Interpreter → + Install packages
    echo.
    pause
    exit /b 1
)
echo ✅ Python dependencies verified

echo [2/6] Starting Docker containers...
docker-compose up -d
timeout /t 5 > nul

echo [3/6] Starting Backend API...
cd Backend
start "Backend API" /B python main.py
cd ..

echo [4/6] Starting Frontend...
cd Frontend
start "Frontend Vue" /B npm run dev
cd ..

echo [5/6] Starting Log Agent...
cd agents
start "Log Agent" /B python log_agent.py --file "..\Examples\example_app.log"
cd ..

echo [6/6] Waiting for components to start...
timeout /t 10 > nul

echo ==========================================
echo           SYSTEM READY!
echo ==========================================
echo Backend API:  http://localhost:8000
echo Frontend:     http://localhost:5173
echo Kibana:       http://localhost:5601
echo Elasticsearch: http://localhost:9200
echo.
echo Press any key to close this window...
pause > nul