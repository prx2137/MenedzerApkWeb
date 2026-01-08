@echo off
chcp 65001 > nul
echo ==========================================
echo   Full Log Management System Startup
echo ==========================================

echo [1/5] Building and starting Docker containers...
docker-compose up -d --build

echo [2/5] Waiting for services to start...
timeout /t 30 > nul

echo [3/5] Checking services status...
echo Elasticsearch: http://localhost:9200
echo Kibana: http://localhost:5601
echo MySQL: localhost:3306
echo Sample API: http://localhost:3000

echo [4/5] Generating sample log files...
cd agents
python log_generator.py
cd ..

echo [5/5] Starting backend and frontend...
cd Backend
start "Backend API" /B python main.py
cd ..

cd Frontend
start "Frontend Vue" /B npm run dev
cd ..

echo ==========================================
echo           SYSTEM READY!
echo ==========================================
echo.
echo 🌐 Management Dashboard: http://localhost:5173
echo 📊 Kibana: http://localhost:5601
echo 🔌 API Endpoints: http://localhost:3000/api
echo 📝 MySQL Database: localhost:3306 (root/rootpassword)
echo.
echo 📋 Useful commands:
echo   docker-compose logs -f        - View all container logs
echo   docker-compose ps             - Check container status
echo   docker-compose restart [service] - Restart specific service
echo.
pause