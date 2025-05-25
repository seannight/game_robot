@echo off
chcp 65001 >nul
echo === 使用Docker启动泰迪杯智能客服系统 ===
echo.

REM 检查Docker是否安装
docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未找到Docker，请先安装Docker
    exit /b 1
)

echo 检测到Docker版本:
docker --version

REM 构建并启动Docker容器
echo 构建并启动Docker容器...
docker-compose up -d

echo.
echo === 启动成功 ===
echo 服务运行在 http://localhost:53085
echo 可以在浏览器中访问上面的地址
echo 使用 docker-compose down 命令停止服务
echo.

REM 自动打开浏览器
start "" http://localhost:53085

pause 