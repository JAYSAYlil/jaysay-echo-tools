@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "JAVA_HOME=%APPDATA%\.minecraft\runtime\java-runtime-gamma-snapshot"
set JAVA_TOOL_OPTIONS=-Djavax.net.ssl.trustStore="C:\Program Files\Eclipse Adoptium\jdk-26.0.2.10-hotspot\lib\security\cacerts" -Djavax.net.ssl.trustStorePassword=changeit
call "%~dp0gradlew.bat" build > "%~dp0build.log" 2>&1
if errorlevel 1 goto build_failed
for /f "tokens=2 delims==" %%V in ('findstr /b "mod_version=" "%~dp0gradle.properties"') do set "ECHOPICKAXE_VERSION=%%V"
for /f "tokens=2 delims==" %%A in ('findstr /b "mod_archive_name=" "%~dp0gradle.properties"') do set "ECHOPICKAXE_ARCHIVE=%%A"
copy /y "%~dp0build\libs\%ECHOPICKAXE_ARCHIVE%-%ECHOPICKAXE_VERSION%.jar" "%~dp0%ECHOPICKAXE_ARCHIVE%-%ECHOPICKAXE_VERSION%.jar" >nul
if errorlevel 1 goto copy_failed
echo Built reobfuscated release: %ECHOPICKAXE_ARCHIVE%-%ECHOPICKAXE_VERSION%.jar
exit /b 0

:build_failed
echo Build failed. See build.log.
pause
exit /b 1

:copy_failed
echo Build succeeded, but the English-named release JAR could not be copied.
pause
exit /b 1
