@echo off
echo =========================================
echo PeopleIN Relay - Local Development Script
echo =========================================
echo.

echo Pulling latest code from GitHub...
git pull origin main
echo.

echo Checking prerequisites...
where go >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Go is not installed! Download it from https://go.dev/dl/
    pause
    exit /b
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed! Download it from https://nodejs.org/
    pause
    exit /b
)

where gcc >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] GCC Compiler is not installed! 
    echo Please install TDM-GCC (https://jmeubank.github.io/tdm-gcc/) so Go can compile the MS Access ODBC drivers.
    pause
    exit /b
)

where wails >nul 2>nul
if %errorlevel% neq 0 (
    echo Wails CLI not found. Installing Wails globally...
    go install github.com/wailsapp/wails/v2/cmd/wails@latest
)

echo.
echo Starting Wails in Hot-Reload Development Mode...
wails dev
