@echo off
TITLE Antigravity SGC Dashboard Launcher

echo ===================================================
echo   Iniciando Dashboard de Ubicaciones...
echo ===================================================

cd /d "c:\Users\Usuario1\Desktop\Antigravity SGC"

echo 1. Iniciando servidor Streamlit...
start "Streamlit Server" /min streamlit run Dashboard.py --server.port 8501 --server.address 127.0.0.1

echo Esperando 5 segundos...
timeout /t 5 /nobreak >nul

echo 2. Iniciando Tunel Cloudflare...
start "Cloudflare Tunnel" /min .\cloudflared.exe tunnel run dashboard-sgc

echo.
echo ===================================================
echo   TODO LISTO!
echo   El dashboard esta corriendo en segundo plano.
echo   No cierres las ventanas minimizadas.
echo ===================================================
timeout /t 10
