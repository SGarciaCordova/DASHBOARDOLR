#!/bin/bash
set -e

echo "============================================"
echo "  🚀 Antigravity SGC — Iniciando..."
echo "============================================"

# ── 1. Inicializar base de datos de autenticación ─────────
echo "📦 Inicializando base de datos de auth..."
python -c "
from auth_system.database import engine, Base
Base.metadata.create_all(bind=engine)
print('✅ Auth DB lista')
"

# ── 2. Inicializar base de datos WMS si no existe ─────────
echo "📦 Inicializando base de datos WMS..."
python -c "
import os, sqlite3
db_path = os.path.join('data', 'wms_data.db')
os.makedirs('data', exist_ok=True)
conn = sqlite3.connect(db_path)
conn.close()
print('✅ WMS DB lista en', db_path)
"

# ── 3. Lanzar Streamlit ───────────────────────────────────
echo "🌐 Lanzando Streamlit en http://0.0.0.0:8501 ..."
exec streamlit run Dashboard.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.headless=true \
  --browser.gatherUsageStats=false
