import socket
import requests
import psutil
import os

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def check_streamlit_running():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'streamlit' in ' '.join(proc.info['cmdline'] or []):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

print("--- DIAGNOSTICO DE RED ---")
print(f"IP Local: {get_ip()}")

if check_port(8501):
    print("✅ Puerto 8501: ABIERTO (Streamlit está escuchando)")
else:
    print("❌ Puerto 8501: CERRADO (Streamlit no está corriendo o está bloqueado)")

if check_streamlit_running():
    print("✅ Proceso Streamlit: DETECTADO (El programa está corriendo)")
else:
    print("❌ Proceso Streamlit: NO DETECTADO")

try:
    response = requests.get('http://localhost:8501/_stcore/health')
    if response.status_code == 200:
        print("✅ Salud de Streamlit: OK (Responde correctamente)")
    else:
        print(f"❌ Salud de Streamlit: ERROR ({response.status_code})")
except Exception as e:
    print(f"❌ Salud de Streamlit: FALLÓ LA CONEXIÓN ({e})")
