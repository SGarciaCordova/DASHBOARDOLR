import streamlit as st

# Persistir navegación en URL para que F5 regrese aquí
_active_page = "projects/Reebok/Airport_Mode_Reebok.py"
st.session_state["_active_page"] = _active_page
st.query_params["page"] = _active_page
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
import json
import base64
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
import pytz

# Configuración Horaria
CDMX_TZ = pytz.timezone('America/Mexico_City')

# ====== DATABASE CONNECTION & CACHING ======
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

def get_db_connection():
    # Mantener para compatibilidad si se usa directamente, pero preferimos SQLAlchemy
    import sqlite3
    conn = sqlite3.connect(os.path.join(BASE_DIR, "data", "wms_data.db"))
    conn.row_factory = sqlite3.Row
    return conn

@st.cache_data(ttl=300, show_spinner=False)
def load_airport_active_data():
    data = {}
    try:
        # 1. Active Orders (wms_aeropuerto view) en Supabase
        query = text("SELECT * FROM wms_aeropuerto")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        data['raw_active'] = df.to_dict(orient='records')
    except Exception as e:
        st.error(f"Error loading active data from Supabase: {e}")
        data['raw_active'] = []

    # Obtener fecha de última sincronización desde audit_logs (Supabase)
    try:
        # Buscamos la última vez que el scraper de Airport Mode inició o terminó con éxito
        log_query = text("""
            SELECT timestamp 
            FROM audit_logs 
            WHERE detail LIKE '%Airport Mode%'
              AND status = 'OK'
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        with engine.connect() as conn:
            res = conn.execute(log_query).fetchone()
            if res:
                # Convertir UTC (Supabase) a CDMX
                last_utc = res[0]
                if last_utc.tzinfo is None:
                    last_utc = pytz.utc.localize(last_utc)
                last_upd = last_utc.astimezone(CDMX_TZ)
                data['last_update'] = last_upd.strftime('%d/%m/%Y %H:%M')
            else:
                # Fallback a la hora actual solo si nunca ha corrido
                data['last_update'] = datetime.now(CDMX_TZ).strftime('%d/%m/%Y %H:%M')
    except Exception:
        data['last_update'] = datetime.now(CDMX_TZ).strftime('%d/%m/%Y %H:%M')
        
    return data

@st.cache_data(ttl=300, show_spinner=False)
def load_airport_shipped_data():
    data = {}
    try:
        # 2. Salidas Recientes desde Supabase (últimos 30 registros de surtido)
        query = text("SELECT * FROM surtido ORDER BY fecha DESC, hora DESC LIMIT 30")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        data['shipped'] = df.to_dict(orient='records')
    except Exception as e:
        st.error(f"Error loading shipped data from Supabase: {e}")
        data['shipped'] = []
    
    return data

def process_data(raw_active, raw_shipped):
    now = datetime.now(CDMX_TZ)
    
    demoras = []
    riesgo = []
    a_tiempo = []
    pending = [] 
    ready = []
    
    for order in raw_active:
        estado = str(order.get('estado', '')).upper().strip()
        f_ingreso_raw = order.get('fecha', '')
        f_entrega_raw = order.get('fecha_entrega', '')
        h_ingreso_raw = order.get('hora', '00:00:00')
        
        # Omitir fecha_cancelación para evitar ruido
        order.pop('fecha_cancelacion', None)

        # 1. Parsear Fecha Ingreso (Punto de partida del SLA)
        try:
            dt_ingreso = pd.to_datetime(f"{str(f_ingreso_raw).split(' ')[0]} {str(h_ingreso_raw)}")
            if dt_ingreso.tzinfo is None:
                dt_ingreso = CDMX_TZ.localize(dt_ingreso)
        except:
            dt_ingreso = now

        # 2. Determinar el Deadline (FECHA ENTREGA o SLA 36h)
        if f_entrega_raw and str(f_entrega_raw).lower() != 'none' and str(f_entrega_raw).strip() != '':
            try:
                deadline = pd.to_datetime(f_entrega_raw)
                if deadline.tzinfo is None:
                    deadline = CDMX_TZ.localize(deadline)
            except:
                deadline = dt_ingreso + timedelta(hours=36)
        else:
            # Fallback a SLA de 36 horas desde la creación
            deadline = dt_ingreso + timedelta(hours=36)

        if estado == 'SURTIDO':
            estado = 'LISTAS PARA EMBARQUE'
            
        # Preparar campos para la visualización
        order['fecha'] = dt_ingreso.strftime("%d/%m/%Y")
        order['hora'] = dt_ingreso.strftime("%H:%M")
        order['estado'] = estado
        order['cliente'] = str(order.get('cliente', '') or '')
        
        # Completitud
        try:
            qty_req = float(order.get('cantidad_pedida', 0) or 0)
            qty_pick = float(order.get('cantidad_surtida', 0) or 0)
            pct = (qty_pick / qty_req * 100.0) if qty_req > 0 else float(str(order.get('tasa_de_cumplimiento', '0')).replace('%', '').strip() or 0)
        except:
            pct = 0
        order['pct_completitud'] = pct

        # Filtrar estados terminados
        if estado in ['EMBARCADO', 'COMPLETO', 'COMPLETADO', 'FINALIZADO', 'CERRADO', 'CLOSED']:
            continue
            
        # Categorización por Proximidad/SLA
        order['_deadline_nice'] = deadline.strftime("%d/%m %H:%M")
        
        if estado == 'LISTAS PARA EMBARQUE' or pct >= 99:
            order['_hours_left'] = None
            ready.append(order)
            continue

        if estado == 'INGRESADO':
            pending.append(order)
            continue

        # Lógica de cálculo de horas restantes
        try:
            # Asegurar que deadline sea offset-aware
            if deadline.tzinfo is None:
                deadline = CDMX_TZ.localize(deadline)

            diff = deadline - now
            hours_left = diff.total_seconds() / 3600.0
            order['_hours_left'] = hours_left
            
            if hours_left < 0: demoras.append(order)
            elif hours_left <= 4: riesgo.append(order)
            else: a_tiempo.append(order)
        except Exception:
            order['_hours_left'] = 999
            a_tiempo.append(order)

    processed_shipped = []
    for s in raw_shipped:
        # Limpieza de campos innecesarios y formateo
        s.pop('fecha_cancelacion', None)
        
        f_val = str(s.get('fecha', '')).split('T')[0]
        h_val = str(s.get('hora', ''))
        
        try:
            dt_s = pd.to_datetime(f"{f_val} {h_val}")
            s['fecha'] = dt_s.strftime("%Y-%m-%d %H:%M")
        except:
            s['fecha'] = f"{f_val} {h_val}".strip() or "Sin fecha"
        
        client_val = s.get('cliente')
        if client_val is None or str(client_val).lower().strip() in ['none', '']:
            s['cliente'] = str(s.get('referencia', s.get('docto_id', 'SIN NOMBRE')))
        else:
            s['cliente'] = str(client_val)
        
        try:
            qty_req = float(s.get('cantidad_pedida', 0) or 0)
            qty_pick = float(s.get('cantidad_surtida', 0) or 0)
            fill_rate = float(s.get('fill_rate', 0) or (qty_pick / qty_req * 100 if qty_req > 0 else 0))
            
            s['completion_text'] = f"{int(qty_pick)} de {int(qty_req)} pzas"
            s['pct_text'] = f"{fill_rate:.1f}%"
            s['pct_completitud'] = fill_rate
        except:
            s['completion_text'] = "N/D"
            s['pct_text'] = "0%"
            s['pct_completitud'] = 0
            
        processed_shipped.append(s)

    return {
        'demoras': demoras,
        'riesgo': riesgo,
        'a_tiempo': a_tiempo,
        'pending': pending,
        'ready': ready,
        'shipped': processed_shipped
    }

def show_airport_mode():
    # Hide Streamlit chrome - Ahora gestionado globalmente en Dashboard.py
    # st.markdown("""
    # <style>
    #     #MainMenu, footer, .stDeployButton { display: none !important; }
    # </style>
    # """, unsafe_allow_html=True)
    
    # st.title("🏗️ Panel de Operaciones Reebok") # Removed to use the one in the topbar


    # Refresh Button
    st.write("")
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.toast("🚀 Iniciando conexión con el WMS...")
        status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_status.json")
        try:
            with open(status_file, "w") as f:
                json.dump({"message": "Iniciando scraper...", "percent": 0, "status": "starting"}, f)
        except: pass
            
        scraper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wms_aeropuerto_scraper.py")
        shipped_scraper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wms_scraper_embarcados.py")
        unify_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unificador.py")

        # Pass user email to scraper via env var
        env = os.environ.copy()
        user_info = st.session_state.get("user", {})
        env["TRIGGERED_BY"] = user_info.get("email", "Unknown") if isinstance(user_info, dict) else getattr(user_info, "email", "Unknown")
        
        with st.status("🏗️ Sincronizando con el servidor...", expanded=True) as status:
            # PHASE 1: ACTIVE ORDERS
            st.write("🛰️ Fase 1: Sincronizando Órdenes Activas...")
            process = subprocess.Popen([sys.executable, scraper_path], shell=False, env=env)
            
            pbar = st.progress(0)
            stext = st.empty()
            
            last_msg = ""
            last_pct = -1
            while True:
                if process.poll() is not None: break
                try:
                    if os.path.exists(status_file):
                        with open(status_file, "r") as f:
                            d = json.load(f)
                            msg = d.get('message', '')
                            percent = d.get('percent', 0)
                            
                            if msg != last_msg or percent != last_pct:
                                stext.info(f"📍 Fase 1: {percent}% — {msg}")
                                last_msg = msg
                                last_pct = percent
                            
                            pbar.progress(percent)
                            
                            if d.get("status") == "error":
                                status.update(label="❌ Error en Fase 1", state="error")
                                break
                except: pass
                time.sleep(0.5)
            
            process.wait()
            
            if process.returncode == 0:
                # PHASE 2: SHIPPED ORDERS (Salidas Recientes)
                st.write("🚛 Fase 2: Sincronizando Salidas Recientes...")
                process2 = subprocess.Popen([sys.executable, shipped_scraper_path], shell=False, env=env)
                
                last_msg = ""
                last_pct = -1
                while True:
                    if process2.poll() is not None: break
                    try:
                        if os.path.exists(status_file):
                            with open(status_file, "r") as f:
                                d = json.load(f)
                                msg = d.get('message', '')
                                percent = d.get('percent', 0)
                                
                                if msg != last_msg or percent != last_pct:
                                    stext.info(f"📍 Fase 2: {percent}% — {msg}")
                                    last_msg = msg
                                    last_pct = percent
                                
                                pbar.progress(percent)
                                
                                if d.get("status") == "error":
                                    status.update(label="❌ Error en Fase 2", state="error")
                                    break
                    except: pass
                    time.sleep(0.5)
                
                process2.wait()
                
                if process2.returncode == 0:
                    # PHASE 3: UNIFY (Deduplication)
                    st.write("🧹 Fase 3: Optimizando base de datos...")
                    subprocess.run([sys.executable, unify_path], shell=False, env=env)
                    
                    status.update(label="✅ Sincronización Exitosa", state="complete", expanded=False)
                    st.success("Todos los datos actualizados (Activos + Salidas).")
                    
                    load_airport_active_data.clear()
                    load_airport_shipped_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    status.update(label="❌ Sincronización Fallida en Fase 2", state="error")
                    st.error("Error al descargar Salidas Recientes.")
            else:
                status.update(label="❌ Sincronización Fallida en Fase 1", state="error")
                st.error("Hubo un error al descargar Órdenes Activas.")

    # Load Data
    # db_mtime removed as we use Supabase now, cache ttl ensures refresh
    
    active_data = load_airport_active_data()
    shipped_data = load_airport_shipped_data()

    processed = process_data(active_data.get('raw_active', []), shipped_data.get('shipped', []))
    total_active = len(processed['demoras']) + len(processed['riesgo']) + len(processed['a_tiempo']) + len(processed['pending']) + len(processed['ready'])
    
    # Metrics for JSON
    json_data = {
        'demoras': processed['demoras'],
        'riesgo': processed['riesgo'],
        'a_tiempo': processed['a_tiempo'],
        'pending': processed['pending'],
        'ready': processed['ready'],
        'shipped': processed['shipped'],
        'counts': {
            'demoras': len(processed['demoras']),
            'riesgo': len(processed['riesgo']),
            'a_tiempo': len(processed['a_tiempo']),
            'ready': len(processed['ready']),
            'pending': len(processed['pending']),
            'shipped': len(processed['shipped']),
            'active': total_active
        },
        'last_update': active_data['last_update']
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
    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            import decimal
            import math
            from datetime import date, time, datetime
            # Handle Decimal (from Postgres/BigQuery)
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            # Handle Date/Time (from Postgres/Pandas)
            if isinstance(obj, (datetime, date, time)):
                return obj.isoformat()
            # Handle potential Numpy/Pandas/Float NaN or Infinity
            if isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None
            try:
                import numpy as np
                if isinstance(obj, (np.floating, np.float64, np.float32)):
                    if np.isnan(obj) or np.isinf(obj):
                        return None
                    return float(obj)
            except: pass
            
            return super(DecimalEncoder, self).default(obj)

    # Use a more flexible replacement in case of minor spacing differences
    json_str = json.dumps(json_data, cls=DecimalEncoder)
    # The file has: const K = /*DATA_PLACEHOLDER*/ {};
    placeholder = '/*DATA_PLACEHOLDER*/ {}'
    if placeholder in js:
        js = js.replace(placeholder, json_str)
    else:
        # Fallback to a broader match if the previous one failed
        # Using string replacement instead of re.sub for security with backslashes
        import re
        match = re.search(r'/\*DATA_PLACEHOLDER\*/\s*\{\}', js)
        if match:
            target = match.group(0)
            js = js.replace(target, json_str)
        else:
            # Last ditch effort if spacing is very different
            js = f"const K = {json_str};\n" + js

    # Parse last update for display
    try:
        last_upd_dt = datetime.strptime(active_data['last_update'], '%d/%m/%Y %H:%M')
        time_display = last_upd_dt.strftime('%H:%M')
        date_display = last_upd_dt.strftime('%A %d %b').capitalize()
    except:
        time_display = "--:--"
        date_display = "---"

    # Load Logo
    logo_path = os.path.join(ASSETS_DIR, 'reebok_logo.png')
    logo_base64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
    
    logo_img_html = f'<img src="data:image/png;base64,{logo_base64}" class="header-logo">' if logo_base64 else '<span style="font-size:2rem;">🏗️</span>'

    # HTML Template — OLR-Style 2-Column Layout
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="1800">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            {css}
            @media (max-width: 768px) {{
                .container-fluid {{
                    grid-template-columns: 1fr;
                    height: auto;
                    padding: 1rem;
                    gap: 1rem;
                }}
                .side-col {{
                    height: auto;
                    max-height: 400px;
                }}
                .stats {{
                    grid-template-columns: repeat(3, 1fr);
                }}
                .order-grid {{
                    grid-template-columns: 1fr;
                }}
                .header-clock {{
                    font-size: 1.8rem;
                }}
                .header-title {{
                    font-size: 1.2rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <!-- LEFT COLUMN: ACTIVE -->
            <div class="main-col">
                <div class="header">
                    <div class="header-title">{logo_img_html} Torre de Control</div>
                    <div class="header-time">
                        <div class="header-clock">{time_display}</div>
                        <div class="header-date">{date_display}</div>
                    </div>
                </div>

                <div class="stats">
                    <div class="stat-card" style="border-left-color: var(--red);" onclick="showCategoryModal('demoras')">
                        <div class="stat-value" style="color: var(--red);">{len(processed['demoras'])}</div>
                        <div class="stat-label" style="color: var(--red);">⚠️ Demorados</div>
                    </div>
                    <div class="stat-card" style="border-left-color: var(--orange);" onclick="showCategoryModal('riesgo')">
                        <div class="stat-value" style="color: var(--orange);">{len(processed['riesgo'])}</div>
                        <div class="stat-label" style="color: var(--orange);">⏰ Riesgo</div>
                    </div>
                    <div class="stat-card" style="border-left-color: var(--blue);" onclick="showCategoryModal('atiempo')">
                        <div class="stat-value" style="color: var(--blue);">{len(processed['a_tiempo'])}</div>
                        <div class="stat-label" style="color: var(--blue);">✓ A Tiempo</div>
                    </div>
                    <div class="stat-card" style="border-left-color: var(--purple);" onclick="showCategoryModal('pending')">
                        <div class="stat-value" style="color: var(--purple);">{len(processed['pending'])}</div>
                        <div class="stat-label" style="color: var(--purple);">📥 Ingresado</div>
                    </div>
                    <div class="stat-card" style="border-left-color: var(--green);" onclick="showCategoryModal('ready')">
                        <div class="stat-value" style="color: var(--green);">{len(processed['ready'])}</div>
                        <div class="stat-label" style="color: var(--green);">🚀 Listas para EMBARQUE</div>
                    </div>
                    <div class="stat-card" style="border-left-color: var(--cyan);" onclick="showCategoryModal('active')">
                        <div class="stat-value" style="color: var(--cyan);">{total_active}</div>
                        <div class="stat-label" style="color: var(--cyan);">📋 Totales</div>
                    </div>
                </div>

                <div class="order-grid" id="orderGrid"></div>
            </div>

            <!-- RIGHT COLUMN: COMPLETED -->
            <div class="side-col">
                <div class="side-title">✅ Salidas Recientes</div>
                <div class="completed-list" id="completedList"></div>
                <div style="margin-top: auto; padding-top: 1rem; text-align: center; font-size: 0.7rem; color: var(--muted);">
                    Actualizado: {active_data['last_update']}
                </div>
            </div>
        </div>

        <!-- Modal -->
        <div class="modal-overlay" id="modalOverlay" onclick="closeModal()">
            <div class="modal-box" id="modalBox" style="display:none;" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <div class="modal-title" id="modalTitle">Detalle de Orden</div>
                    <button class="close-btn" onclick="closeModal()">×</button>
                </div>
                <div id="modalContent"></div>
                <div class="modal-footer">
                    <button class="btn-close" onclick="closeModal()">Cerrar</button>
                </div>
            </div>
        </div>

        <script>
            {js}
        </script>
    </body>
    </html>
    """

    components.html(html_content, height=900, scrolling=True)

# Solo se ejecuta si se corre directamente, pero st.navigation corre el script completo
show_airport_mode()
