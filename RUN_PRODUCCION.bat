@echo off
TITLE Antigravity SGC Dashboard - PRODUCTION MODE (No Tunnel)
echo ===================================================
echo   Iniciando Dashboard Operativo...
echo ===================================================

cd /d "c:\Users\Usuario1\Desktop\Antigravity SGC"

echo 0. Estableciendo IP Estatica (192.168.100.242)...
powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "set_static_ip.ps1"

echo 1. Iniciando servidor Streamlit (Puerto 8501)...
:: Usamos el entorno virtual para asegurar que todas las dependencias (Supabase, etc) esten presentes
start "Streamlit Server" /min .\.venv\Scripts\python.exe -m streamlit run Dashboard.py --server.port 8501 --server.address 0.0.0.0

echo 2. Iniciando Bot Launcher (Scraper)...
start "Bot Launcher" /min .\.venv\Scripts\python.exe bot_launcher.py

echo Esperando validacion...
timeout /t 3 /nobreak >nul

echo.
echo ===================================================
echo   TODO LISTO!
echo   El dashboard esta corriendo en segundo plano.
echo   Acceso Local WiFi: http://192.168.100.242:8501
echo ===================================================
timeout /t 5
