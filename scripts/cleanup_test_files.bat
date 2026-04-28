@echo off
REM 清理测试文件 - Windows批处理脚本

set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%cleanup_test_files.py"

if not exist "%PYTHON_SCRIPT%" (
    echo 错误：找不到Python脚本 %PYTHON_SCRIPT%
    exit /b 1
)

REM 尝试运行Python脚本
python "%PYTHON_SCRIPT%" %*

if errorlevel 1 (
    echo.
    echo Python脚本执行失败，请检查Python是否安装
    echo.
    echo 或者您可以手动删除以下目录：
    echo   - test_*
    echo   - tmp*
)
