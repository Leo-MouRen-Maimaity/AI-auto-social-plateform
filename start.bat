@echo off
echo === AI社区项目启动脚本 ===
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请安装Python 3.10+
    pause
    exit /b 1
)

REM 创建虚拟环境
if not exist "venv" (
    echo 创建Python虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境并安装依赖
echo 安装Python依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

REM 初始化数据库
echo 请确保MySQL已启动，然后手动执行:
echo mysql -u root -p < data/migrations/001_init.sql
echo.

REM 启动后端
echo 启动FastAPI后端服务...
start "API Server" cmd /k "call venv\Scripts\activate.bat && cd /d %~dp0 && python -m uvicorn api_server.main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo 后端已启动: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.

REM 前端提示
echo 启动前端请执行:
echo   cd web_frontend
echo   npm install
echo   npm run dev
echo.
pause
