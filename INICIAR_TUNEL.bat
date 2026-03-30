@echo off
TITLE Cloudflare Tunnel Handler - DASHBOARD SGC
echo ===================================================
echo   Iniciando Tunel Seguro para Acceso Externo...
echo ===================================================

cd /d "%~dp0"

if not exist "cloudflared.exe" (
    echo ERROR: No se encuentra cloudflared.exe en este directorio.
    pause
    exit /b
)

echo 1. Conectando al tunel: dashboard-sgc...
echo (Este servicio permitira que el dashboard sea visible desde fuera de la red local)
echo.

.\cloudflared.exe tunnel run dashboard-sgc

echo.
echo Tunnel cerrado.
pause
