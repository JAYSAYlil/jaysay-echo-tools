@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "ARGS="
:parse
if "%~1"=="" goto run
if /i "%~1"=="--smoke"    set "ARGS=%ARGS% -Smoke"
if /i "%~1"=="--install"  set "ARGS=%ARGS% -Install"
if /i "%~1"=="--world"    set "ARGS=%ARGS% -World "%~2"" & shift
if /i "%~1"=="--instance" set "ARGS=%ARGS% -InstancePath "%~2"" & shift
shift
goto parse
:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\acceptance.ps1" %ARGS%
exit /b %errorlevel%
