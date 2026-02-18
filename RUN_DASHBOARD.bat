@echo off
TITLE Antigravity Dashboard Launcher
cd /d "%~dp0"
echo Iniciando Dashboard...
.\.venv\Scripts\python.exe -m streamlit run Dashboard.py --server.port 8501 --server.address 127.0.0.1
pause
