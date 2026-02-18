import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import json
import os
import subprocess
import sys
import time
from datetime import datetime

# ====== DATABASE CONNECTION & CACHING ======
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "wms_data.db")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@st.cache_data(ttl=300, show_spinner=False)
def load_airport_data(db_path_mtime):
    conn = get_db_connection()
    data = {}
    
    # 1. Active Orders (wms_aeropuerto view)
    try:
        try:
            active_raw = conn.execute("SELECT * FROM wms_aeropuerto").fetchall()
        except Exception:
            active_raw = []
        data['raw_active'] = [dict(row) for row in active_raw]
    except:
        data['raw_active'] = []

    # 2. Shipped Orders (Last 50)
    try:
        shipped = conn.execute("SELECT * FROM inbound_scord_despachados_raw ORDER BY fecha DESC LIMIT 50").fetchall()
        data['shipped'] = [dict(row) for row in shipped]
    except:
        data['shipped'] = []
    
    # Last Update
    data['last_update'] = datetime.fromtimestamp(os.path.getmtime(DB_PATH)).strftime('%d/%m/%Y %H:%M') if os.path.exists(DB_PATH) else datetime.now().strftime('%d/%m/%Y %H:%M')
    
    conn.close()
    return data

def process_data(raw_active, raw_shipped):
    now = datetime.now()
    
    demoras = []
    riesgo = []
    a_tiempo = []
    pending = [] 
    
    for order in raw_active:
        estado = str(order.get('estado', '')).upper().strip()
        f_str = str(order.get('fecha', '')).strip()
        h_str = str(order.get('hora', '00:00:00')).strip() or '00:00:00'
        
        if 'T' in f_str: dt_str = f_str.split('T')[0]
        else: dt_str = f_str
        
        order['fecha'] = dt_str
        order['hora'] = h_str
        order['estado'] = estado
        
        try:
            qty_req = float(order.get('cantidad_pedida', 0) or 0)
            qty_pick = float(order.get('cantidad_surtida', 0) or 0)
            pct = (qty_pick / qty_req * 100) if qty_req > 0 else 0
        except:
            pct = 0
        order['pct_completitud'] = pct

        if estado == 'INGRESADO':
            pending.append(order)
            continue
            
        if estado == 'SURTIDO':
            # Treat as completed/shipped
            shipped_order = order.copy()
            # Normalize date for shipped display
            f_val = str(shipped_order.get('fecha', '')).strip()
            h_val = str(shipped_order.get('hora', '00:00:00')).strip()
            shipped_order['fecha'] = f"{f_val} {h_val}"
            raw_shipped.append(shipped_order)
            continue

        # If it reaches here, it's 'SURTIENDOSE' or other active state
        try:
            full_str = f"{dt_str} {h_str}"
            try: deadline = datetime.strptime(full_str, "%Y-%m-%d %H:%M:%S")
            except: 
                try: deadline = datetime.strptime(full_str, "%Y-%m-%d %H:%M")
                except: deadline = datetime.combine(datetime.strptime(dt_str, "%Y-%m-%d").date(), datetime.max.time())

            diff = deadline - now
            hours_left = diff.total_seconds() / 3600.0
            order['_hours_left'] = hours_left
            order['_deadline_nice'] = deadline.strftime("%d/%m %H:%M")
            
            if hours_left < 0: demoras.append(order)
            elif hours_left <= 4: riesgo.append(order)
            else: a_tiempo.append(order)
        except:
            order['_hours_left'] = 999
            order['_deadline_nice'] = f"{dt_str} {h_str}"
            a_tiempo.append(order)

    processed_shipped = []
    for s in raw_shipped:
        s_estado = str(s.get('estado', '')).upper().strip()
        if s_estado == 'SURTIDO':
            s['fecha'] = str(s.get('fecha', '')).replace('T', ' ').split('.')[0]
            processed_shipped.append(s)
            
    return {
        'demoras': demoras,
        'riesgo': riesgo,
        'a_tiempo': a_tiempo,
        'pending': pending,
        'shipped': processed_shipped
    }

def show_airport_mode():
    # Hide Streamlit chrome
    st.markdown("""
    <style>
        #MainMenu, footer, .stDeployButton { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    
    # st.title("🏗️ Panel de Operaciones Reebok") # Removed to use the one in the topbar


    # Refresh Button
    if st.button("🔄 Refrescar Datos Aeropuerto"):
        status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_status.json")
        try:
            with open(status_file, "w") as f:
                json.dump({"message": "Iniciando...", "percent": 0, "status": "starting"}, f)
        except: pass
            
        scraper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wms_aeropuerto_scraper.py")
        process = subprocess.Popen([sys.executable, scraper_path], shell=False)
        
        pbar = st.progress(0)
        stext = st.empty()
        
        while True:
            if process.poll() is not None: break
            try:
                if os.path.exists(status_file):
                    with open(status_file, "r") as f:
                        d = json.load(f)
                        pbar.progress(d.get("percent", 0))
                        stext.info(f"{d.get('message', '')}")
            except: pass
            time.sleep(1)
        
        process.wait()
        if process.returncode == 0:
            st.success("Actualizado")
            load_airport_data.clear()
            st.rerun()
        else:
            st.error("Error al actualizar")

    # Load Data
    try: db_mtime = os.path.getmtime(DB_PATH)
    except: db_mtime = 0
    app_data = load_airport_data(db_mtime)

    processed = process_data(app_data.get('raw_active', []), app_data.get('shipped', []))

    # Metrics for JSON
    json_data = {
        'demoras': processed['demoras'],
        'riesgo': processed['riesgo'],
        'a_tiempo': processed['a_tiempo'],
        'pending': processed['pending'],
        'shipped': processed['shipped'],
        'counts': {
            'demoras': len(processed['demoras']),
            'riesgo': len(processed['riesgo']),
            'a_tiempo': len(processed['a_tiempo']),
            'shipped': len(processed['shipped'])
        },
        'last_update': app_data['last_update']
    }

    # Load Assets
    try:
        with open(os.path.join(ASSETS_DIR, 'reebok_airport_style.css'), 'r', encoding='utf-8') as f:
            css = f.read()
        with open(os.path.join(ASSETS_DIR, 'reebok_airport_dashboard.js'), 'r', encoding='utf-8') as f:
            js = f.read()
    except Exception as e:
        st.error(f"Error loading assets: {e}")
        css, js = "", ""

    # Inject Data
    js = js.replace('/*DATA_PLACEHOLDER*/ {}', json.dumps(json_data))

    # Parse last update for display
    try:
        last_upd_dt = datetime.strptime(app_data['last_update'], '%d/%m/%Y %H:%M')
        time_display = last_upd_dt.strftime('%H:%M')
        date_display = last_upd_dt.strftime('%d/%m/%Y')
    except:
        time_display = "--:--"
        date_display = "---"


    # HTML Template
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            {css}
        </style>
    </head>
    <body>
        <div class="topbar">
            <div class="header-title">
                <span style="font-size:2rem;">✈️</span> Airport Mode Reebok
            </div>
            <div class="header-time">
                <div class="header-clock">{time_display}</div>
                <div class="header-date">{date_display}</div>
                <div class="tag green" style="display: inline-block; margin-top: 5px;">● EN LÍNEA</div>
            </div>
        </div>

        <div class="container">
            <!-- METRIC CARDS -->
            <div class="section-title">📊 Resumen Operativo</div>
            <div class="grid-4">
                <div class="card" onclick="showModal('demoras')">
                    <div class="card-header"><div class="card-label">Demoras</div><div class="card-icon" style="background:#fee2e2;">🔥</div></div>
                    <div class="card-value red">{len(processed['demoras'])}</div>
                    <div class="card-footer">Vencidos (< 0h)</div>
                </div>
                <div class="card" onclick="showModal('riesgo')">
                    <div class="card-header"><div class="card-label">En Riesgo</div><div class="card-icon" style="background:#ffedd5;">⚠️</div></div>
                    <div class="card-value orange">{len(processed['riesgo'])}</div>
                    <div class="card-footer">Críticos (0 - 4h)</div>
                </div>
                <div class="card" onclick="showModal('atiempo')">
                    <div class="card-header"><div class="card-label">A Tiempo</div><div class="card-icon" style="background:#dcfce7;">✅</div></div>
                    <div class="card-value green">{len(processed['a_tiempo'])}</div>
                    <div class="card-footer">En órden (> 4h)</div>
                </div>
                <div class="card" onclick="showModal('shipped')">
                    <div class="card-header"><div class="card-label">Salidas</div><div class="card-icon" style="background:#dbeafe;">🛫</div></div>
                    <div class="card-value blue">{len(processed['shipped'])}</div>
                    <div class="card-footer">Últimas 50 salidas</div>
                </div>
            </div>

            <!-- LISTS SECTION -->
            <div class="list-container">
                <!-- Left Column: Critical & Pending -->
                <div class="list-col">
                    <div class="list-header">
                         <span>⚠️ Críticos & Riesgo</span>
                         <span class="tag orange">{len(processed['demoras']) + len(processed['riesgo'])}</span>
                    </div>
                    <div class="list-body" id="list-critical">
                        <!-- JS Injected -->
                    </div>
                    <!-- Pending Sub-section -->
                    <div class="list-header" style="border-top:1px solid #e2e8f0; margin-top:auto;">
                        <span>📋 Pendientes (Ingresados)</span>
                        <span class="tag blue" style="background:#f1f5f9; color:#475569;">{len(processed['pending'])}</span>
                    </div>
                    <div class="list-body" id="list-pending" style="height:35%;">
                         <!-- JS Injected -->
                    </div>
                </div>

                <!-- Right Column: Recent Shipments -->
                <div class="list-col">
                    <div class="list-header">
                        <span>🛫 Salidas Recientes</span>
                        <span class="tag blue">{len(processed['shipped'])}</span>
                    </div>
                    <div class="list-body" id="list-shipped">
                        <!-- JS Injected -->
                    </div>
                </div>
            </div>

        </div>

        <!-- MODAL -->
        <div class="modal-overlay" id="modalOverlay" onclick="closeModal()">
            <div class="modal-box" id="modalBox" style="display:none;" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <div class="modal-title" id="modalTitle">Detalle</div>
                    <button class="close-btn" onclick="closeModal()">×</button>
                </div>
                <div id="modalContent"></div>
            </div>
        </div>

        <script>
            {js}
        </script>
    </body>
    </html>
    """

    components.html(html_content, height=1000, scrolling=False)

if __name__ == "__main__":
    show_airport_mode()
