@echo off
echo ===================================
echo   竞赛智能客服系统 - 启动与测试工具
echo ===================================
echo.

REM 检查Python环境
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未找到Python，请确保Python已安装并添加到PATH环境变量中
    goto :end
)

REM 创建必要的目录
if not exist logs mkdir logs
if not exist test_results mkdir test_results

echo 请选择操作:
echo 1. 启动系统
echo 2. 运行API测试
echo 3. 重建索引
echo 4. 启动系统并在新窗口中运行API测试
echo 5. 退出
echo.

:menu
set /p choice=请输入选项 (1-5): 

if "%choice%"=="1" goto start_system
if "%choice%"=="2" goto run_api_test
if "%choice%"=="3" goto rebuild_index
if "%choice%"=="4" goto start_and_test
if "%choice%"=="5" goto end
echo 无效选项，请重新输入
goto menu

:start_system
echo 正在启动竞赛智能客服系统...
echo 系统启动后，可通过 http://localhost:53085 访问
start cmd /k "python -m app.main"
echo 系统启动完成，请在浏览器中访问 http://localhost:53085
goto end

:run_api_test
echo 正在运行API测试...
python test_api.py
goto end

:rebuild_index
echo 正在重建索引...
python force_rebuild_index.py
goto end

:start_and_test
echo 正在启动系统并准备测试...
start cmd /k "python -m app.main"
echo 等待系统启动 (5秒)...
timeout /t 5 /nobreak >nul
echo 正在运行API测试...
start cmd /k "python test_api.py"
echo 系统已启动，测试正在运行
echo 系统可通过 http://localhost:53085 访问
goto end

:end
echo.
echo 操作完成