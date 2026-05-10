@echo off
REM ============================================================
REM   Aether Guide — 一键启动
REM   双击本文件即可启动 API + 游客端 + 管理端,并自动打开浏览器
REM
REM   可选参数会原样透传给 scripts\start.ps1,例如:
REM     start.cmd -NoAdmin
REM     start.cmd -Docker -Clean
REM ============================================================

setlocal
cd /d "%~dp0"

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell not found in PATH.
    echo         Please install Windows PowerShell 5.1+ or PowerShell 7.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [exit code %EXIT_CODE%] Press any key to close this window.
    pause >nul
)
exit /b %EXIT_CODE%
