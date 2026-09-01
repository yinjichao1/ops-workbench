@echo off
chcp 65001 >nul
title 思格教育 · 运营工作台
echo.
echo    ====================================
echo      思格教育 · 新媒体运营工作台
echo    ====================================
echo.
echo    [1] 本地模式（各人独立数据）
echo    [2] 共享模式（三人共用数据）
echo.
set /p mode=    请选择 (1/2): 

:: Python check
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo    [错误] 请先安装 Python
    echo    https://www.python.org/downloads/
    echo    安装时勾选 "Add Python to PATH"
    pause
    exit /b 1
)

:: Create venv
if not exist "venv\" (
    echo    [1/3] 创建虚拟环境...
    python -m venv venv
)

:: Install deps
echo    [2/3] 安装依赖...
venv\Scripts\pip install -q fastapi uvicorn sqlalchemy python-multipart aiofiles openpyxl >nul 2>&1

:: Shared mode
if "%mode%"=="2" (
    echo.
    echo    请输入共享数据库路径，例如:
    echo    Z:\team\ops_workbench.db
    echo    \\192.168.1.100\share\ops_workbench.db
    echo.
    set /p dbpath=    路径: 
    set OPS_DB_PATH=%dbpath%
    echo.
    echo    数据库 = %OPS_DB_PATH%
)

:: Start
echo    [3/3] 启动服务...
echo.
echo    ┌──────────────────────────────────────┐
echo    │   打开浏览器: http://localhost:8000  │
echo    │   按 Ctrl+C 停止                     │
echo    └──────────────────────────────────────┘
echo.
venv\Scripts\python run.py
pause
