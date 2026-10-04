@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "JAVA_HOME=%APPDATA%\.minecraft\runtime\java-runtime-gamma-snapshot"
if not exist "%JAVA_HOME%\bin\java.exe" (
  echo Minecraft Java 17 runtime not found: %JAVA_HOME%
  pause
  exit /b 1
)
set JAVA_TOOL_OPTIONS=-Djavax.net.ssl.trustStore="C:\Program Files\Eclipse Adoptium\jdk-26.0.2.10-hotspot\lib\security\cacerts" -Djavax.net.ssl.trustStorePassword=changeit
call "%~dp0gradlew.bat" runClient > "%~dp0client.log" 2>&1
if errorlevel 1 pause
