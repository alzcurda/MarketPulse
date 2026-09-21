@echo off
title MarketPulse Web Server
echo ========================================================
echo   Iniciando MarketPulse Web (Servidor Local)
echo ========================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo Usando entorno virtual: .venv
    .venv\Scripts\python.exe -m marketpulse.web
) else (
    echo Usando Python del sistema...
    python -m marketpulse.web
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un error al ejecutar MarketPulse Web.
    pause
)
