@echo off
chcp 65001 >nul
echo ========================================
echo   城市低空物流运营中心 (LALOC) 启动脚本
echo ========================================
echo.

echo [1/3] 启动数据库 (Docker)...
cd backend
docker compose up -d
if errorlevel 1 (
    echo [错误] Docker 启动失败，请确保 Docker Desktop 已运行
    pause
    exit /b 1
)
echo [1/3] 数据库已启动 (端口 5433)
echo.

echo [2/3] 启动后端服务...
start "LALOC Backend" cmd /k "venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo [2/3] 后端启动中... (http://localhost:8000)
echo.

echo [3/3] 启动前端服务...
cd ..\frontend
start "LALOC Frontend" cmd /k "npm run dev"
echo [3/3] 前端启动中... (http://localhost:5173)
echo.

echo ========================================
echo   所有服务已启动！
echo.
echo   前端页面:  http://localhost:5173
echo   后端文档:  http://localhost:8000/docs
echo.
echo   关闭方法: 分别关闭两个弹出的终端窗口，
echo   然后运行 docker compose down
echo ========================================
echo.
pause
