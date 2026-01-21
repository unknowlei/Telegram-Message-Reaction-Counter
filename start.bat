@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: 设置 Python UTF-8 模式，避免中文编码问题
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: ============================================
:: Telegram Reaction Counter - 一键启动脚本
:: ============================================

title Telegram Reaction Counter

:: 颜色设置
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "CYAN=[96m"
set "RESET=[0m"

echo.
echo %CYAN%╔════════════════════════════════════════════════════════════╗%RESET%
echo %CYAN%║                                                            ║%RESET%
echo %CYAN%║   📊 Telegram Reaction Counter                             ║%RESET%
echo %CYAN%║                                                            ║%RESET%
echo %CYAN%╚════════════════════════════════════════════════════════════╝%RESET%
echo.

:: 获取脚本所在目录
cd /d "%~dp0"

:: ============================================
:: 步骤1：检查 Python
:: ============================================
echo %YELLOW%[1/4] 检查 Python 环境...%RESET%

python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%✗ 错误: 未找到 Python%RESET%
    echo.
    echo 请先安装 Python 3.8 或更高版本:
    echo   https://www.python.org/downloads/
    echo.
    echo 安装时请勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo %GREEN%✓ 已找到 Python %PYTHON_VERSION%%RESET%

:: ============================================
:: 步骤2：检查/创建虚拟环境
:: ============================================
echo.
echo %YELLOW%[2/4] 检查虚拟环境...%RESET%

if not exist "venv" (
    echo   正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo %RED%✗ 创建虚拟环境失败%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%✓ 虚拟环境创建成功%RESET%
    set "NEED_INSTALL=1"
) else (
    echo %GREEN%✓ 虚拟环境已存在%RESET%
    set "NEED_INSTALL=0"
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: ============================================
:: 步骤3：安装依赖
:: ============================================
echo.
echo %YELLOW%[3/4] 检查依赖...%RESET%

:: 检查是否需要安装依赖
pip show flask >nul 2>&1
if errorlevel 1 set "NEED_INSTALL=1"

pip show telethon >nul 2>&1
if errorlevel 1 set "NEED_INSTALL=1"

if "%NEED_INSTALL%"=="1" (
    echo   正在安装依赖，请稍候...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo %RED%✗ 安装依赖失败%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%✓ 依赖安装成功%RESET%
) else (
    echo %GREEN%✓ 依赖已安装%RESET%
)

:: ============================================
:: 步骤4：检查配置文件
:: ============================================
echo.
echo %YELLOW%[4/4] 检查配置文件...%RESET%

if not exist "config.py" (
    echo.
    echo %YELLOW%═══════════════════════════════════════════════════════════════%RESET%
    echo %YELLOW%  首次使用，需要配置 Telegram API 凭证%RESET%
    echo %YELLOW%═══════════════════════════════════════════════════════════════%RESET%
    echo.
    echo   请按以下步骤获取凭证：
    echo   1. 打开浏览器访问: https://my.telegram.org
    echo   2. 使用你的 Telegram 手机号登录
    echo   3. 点击 "API development tools"
    echo   4. 填写应用信息（App title 和 Short name 随便填）
    echo   5. 点击 "Create application"
    echo   6. 记录显示的 api_id 和 api_hash
    echo.
    
    :: 自动打开 my.telegram.org
    echo   正在打开 my.telegram.org ...
    start https://my.telegram.org
    echo.
    
    :: 等待用户获取凭证
    echo   获取凭证后，请在下方输入:
    echo.
    
    :INPUT_API_ID
    set /p "API_ID=  请输入 API ID (纯数字): "
    
    :: 验证是否为数字（使用延迟展开）
    set "VALID=1"
    for /f "delims=0123456789" %%i in ("!API_ID!") do set "VALID=0"
    if "!API_ID!"=="" set "VALID=0"
    
    if "!VALID!"=="0" (
        echo   %RED%✗ 无效的 API ID，请输入纯数字%RESET%
        goto INPUT_API_ID
    )
    
    echo.
    set /p "API_HASH=  请输入 API Hash (字母数字): "
    
    if "!API_HASH!"=="" (
        echo   %RED%✗ API Hash 不能为空%RESET%
        goto INPUT_API_ID
    )
    
    :: 从模板创建配置文件
    echo.
    echo   正在创建配置文件...
    
    (
        echo """
        echo Telegram API 配置文件
        echo """
        echo.
        echo # Telegram API 凭证
        echo API_ID = !API_ID!
        echo API_HASH = "!API_HASH!"
        echo.
        echo # 会话名称
        echo SESSION_NAME = "telegram_session"
        echo.
        echo # 以下配置可以在 Web 界面中设置
        echo TARGET_CHANNEL = ""
        echo MAX_MESSAGES = 1000
        echo MIN_REACTIONS = 5
        echo MEDIA_ONLY = True
        echo BATCH_DELAY = 1.0
        echo BATCH_SIZE = 100
        echo OUTPUT_DIR = "output"
        echo OUTPUT_FILENAME = "top_messages"
        echo OUTPUT_FORMAT = "both"
        echo TOP_N_DISPLAY = 20
    ) > config.py
    
    echo %GREEN%✓ 配置文件创建成功！%RESET%
    echo.
) else (
    echo %GREEN%✓ 配置文件已存在%RESET%
)

:: ============================================
:: 启动 Web 应用
:: ============================================
echo.
echo %GREEN%═══════════════════════════════════════════════════════════════%RESET%
echo %GREEN%  ✓ 所有检查通过，正在启动 Web 应用...%RESET%
echo %GREEN%═══════════════════════════════════════════════════════════════%RESET%
echo.
echo   Web 地址: %CYAN%http://localhost:5000%RESET%
echo.
echo   按 %YELLOW%Ctrl+C%RESET% 可停止服务
echo.

:: 等待1秒后打开浏览器
timeout /t 1 /nobreak >nul
start http://localhost:5000

:: 启动 Flask 应用
python web_app.py

:: 如果应用退出
echo.
echo %YELLOW%Web 应用已停止%RESET%
pause