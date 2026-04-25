@echo off
REM 清理测试文件批处理脚本
REM 用法: cleanup_test_files.bat [DIR] [--all]

python "%~dp0cleanup_test_files.py" %*
