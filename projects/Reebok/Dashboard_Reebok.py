import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import json
import os
from datetime import datetime, timedelta
import subprocess
import time
import sys
import pandas as pd
import pytz

# Configuración Horaria
CDMX_TZ = pytz.timezone('America/Mexico_City')

# st.set_page_config(
#     page_title="Dashboard Reebok",
#     page_icon="👟",
#     layout="wide",
#     initial_sidebar_state="collapsed",
# )

# Hide Streamlit chrome - Ahora gestionado globalmente en Dashboard.py
# st.markdown("""
# <style>
#     #MainMenu, footer, .stDeployButton { display: none !important; }
# </style>
# """, unsafe_allow_html=True)

# ====== DATABASE CONNECTION & CACHING ======
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.ai_summarizer import get_ai_insight, clear_ai_cache

def get_db_connection():
    # Mantener para compatibilidad si se usa directamente, pero preferimos SQLAlchemy
    import sqlite3
    conn = sqlite3.connect(os.path.join(BASE_DIR, "data", "wms_data.db"))
    conn.row_factory = sqlite3.Row
    return conn

def get_cooldown_status(minutes):
    try:
        from sqlalchemy import text
        import pytz
        from datetime import datetime
        import os
        import json
        CDMX_TZ_LOCAL = pytz.timezone('America/Mexico_City')
        
        with engine.connect() as conn:
            result = conn.execute(text('SELECT "timestamp" FROM audit_logs WHERE event_type = \'SYNC\' ORDER BY "timestamp" DESC LIMIT 1')).fetchone()
            if not result:
                return True, 0
            
            last_run_raw = result[0]
            if last_run_raw.tzinfo is None:
                last_run_cdmx = pytz.utc.localize(last_run_raw).astimezone(CDMX_TZ_LOCAL)
            else:
                last_run_cdmx = last_run_raw.astimezone(CDMX_TZ_LOCAL)
                
            now_cdmx = datetime.now(CDMX_TZ_LOCAL)
            elapsed = now_cdmx - last_run_cdmx
            elapsed_minutes = elapsed.total_seconds() / 60
            
            if elapsed_minutes < minutes:
                return False, round(minutes - elapsed_minutes, 1)
            else:
                return True, 0
    except Exception as e:
        import os
        import json
        from datetime import datetime
        cooldown_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_cooldown.json")
        if not os.path.exists(cooldown_file): return True, 0
        try:
            with open(cooldown_file, "r") as f:
                data = json.load(f)
                last_run = datetime.fromisoformat(data.get("last_run"))
                now = datetime.now()
                elapsed = now - last_run
                elapsed_minutes = elapsed.total_seconds() / 60
                if elapsed_minutes < minutes: return False, round(minutes - elapsed_minutes, 1)
        except: pass
        return True, 0

def save_last_run_now():
    import os
    import json
    from datetime import datetime
    cooldown_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_cooldown.json")
    try:
        with open(cooldown_file, "w") as f:
            json.dump({"last_run": datetime.now().isoformat()}, f)
    except Exception:
        pass


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_raw_data_from_db(dummy_param=None):
    try:
        with engine.connect() as conn:
            import pandas as pd
            df_entradas = pd.read_sql("SELECT docto_id, referencia, fecha, sku, descripcion, cantidad, calidad, tarimas FROM entradas WHERE docto_id IS NOT NULL AND docto_id != ''", conn)
            df_surtido = pd.read_sql("SELECT docto_id, referencia, fecha, hora, cantidad_pedida, cantidad_surtida, tarimas, estado, fill_rate FROM surtido WHERE UPPER(TRIM(estado)) != 'INGRESADO'", conn)
            
            # Filtro fechas nulas y format
            df_entradas = df_entradas[df_entradas['fecha'].notna() & (df_entradas['fecha'].astype(str).str.strip() != '')].copy()
            df_surtido = df_surtido[df_surtido['fecha'].notna() & (df_surtido['fecha'].astype(str).str.strip() != '')].copy()

            df_entradas['fecha_dt'] = pd.to_datetime(df_entradas['fecha'].astype(str).str[:10], format='%d/%m/%Y', errors='coerce').dt.date
            df_surtido['fecha_dt'] = pd.to_datetime(df_surtido['fecha'].astype(str), errors='coerce').dt.date

            # Clean fill_rate and numeric cols just in case
            numeric_cols_in = ['cantidad', 'tarimas']
            for col in numeric_cols_in:
                df_entradas[col] = pd.to_numeric(df_entradas[col], errors='coerce').fillna(0)
                
            numeric_cols_out = ['cantidad_surtida', 'cantidad_pedida', 'tarimas', 'fill_rate']
            for col in numeric_cols_out:
                df_surtido[col] = pd.to_numeric(df_surtido[col], errors='coerce').fillna(0)

            return df_entradas, df_surtido
    except Exception as e:
        print("Error fetching cache DB data:", e)
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=300, show_spinner=False)
def load_all_data_filtered(start_date=None, end_date=None, dummy_param=None):
    df_entradas_raw, df_surtido_raw = fetch_raw_data_from_db(dummy_param)
    data = {}
    
    # Manejar caso sin tablas
    if 'docto_id' not in df_entradas_raw.columns:
        return {
            'total_recibos': 0, 'piezas_recibidas': 0, 'skus_unicos': 0, 'tarimas_recibidas': 0, 'tasa_calidad': 0,
            'total_pedidos': 0, 'piezas_surtidas': 0, 'total_pedida': 0, 'fill_rate': 0, 'tarimas_despachadas': 0, 'pct_completados': 0,
            'last_update': "N/A", 'entradas_data': [], 'surtido_data': [], 'chart_entradas': [], 'chart_surtido': [],
            'chart_skus': [], 'chart_calidad': [], 'chart_tarimas_in': [], 'chart_tarimas_out': [], 'chart_estado': [], 'chart_fillrate': []
        }

    if start_date and end_date:
        df_entradas = df_entradas_raw[(df_entradas_raw['fecha_dt'] >= start_date) & (df_entradas_raw['fecha_dt'] <= end_date)].copy()
        df_surtido = df_surtido_raw[(df_surtido_raw['fecha_dt'] >= start_date) & (df_surtido_raw['fecha_dt'] <= end_date)].copy()
        
        diff_days = (end_date - start_date).days + 1
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=diff_days - 1)
        
        df_entradas_prev = df_entradas_raw[(df_entradas_raw['fecha_dt'] >= prev_start_date) & (df_entradas_raw['fecha_dt'] <= prev_end_date)]
        df_surtido_prev = df_surtido_raw[(df_surtido_raw['fecha_dt'] >= prev_start_date) & (df_surtido_raw['fecha_dt'] <= prev_end_date)]
        
        df_entradas_ai = df_entradas.copy()
        df_surtido_ai = df_surtido.copy()
    else:
        df_entradas = df_entradas_raw.copy()
        df_surtido = df_surtido_raw.copy()
        
        today_dt = datetime.now().date()
        ai_curr_start = today_dt - timedelta(days=7)
        ai_curr_end = today_dt
        df_entradas_ai = df_entradas_raw[(df_entradas_raw['fecha_dt'] >= ai_curr_start) & (df_entradas_raw['fecha_dt'] <= ai_curr_end)]
        df_surtido_ai = df_surtido_raw[(df_surtido_raw['fecha_dt'] >= ai_curr_start) & (df_surtido_raw['fecha_dt'] <= ai_curr_end)]
        
        ai_prev_end = ai_curr_start - timedelta(days=1)
        ai_prev_start = ai_prev_end - timedelta(days=7)
        df_entradas_prev = df_entradas_raw[(df_entradas_raw['fecha_dt'] >= ai_prev_start) & (df_entradas_raw['fecha_dt'] <= ai_prev_end)]
        df_surtido_prev = df_surtido_raw[(df_surtido_raw['fecha_dt'] >= ai_prev_start) & (df_surtido_raw['fecha_dt'] <= ai_prev_end)]

    # INBOUND
    data['total_recibos'] = df_entradas['docto_id'].nunique() if not df_entradas.empty else 0
    data['piezas_recibidas'] = float(df_entradas['cantidad'].sum()) if not df_entradas.empty else 0
    data['skus_unicos'] = df_entradas['sku'].nunique() if not df_entradas.empty else 0
    data['tarimas_recibidas'] = float(df_entradas['tarimas'].sum()) if not df_entradas.empty else 0
    
    if not df_entradas.empty:
        valid_cal = df_entradas[df_entradas['calidad'].astype(str).str.strip() != '']
        t_cal = len(valid_cal)
        c_a = len(valid_cal[valid_cal['calidad'].astype(str).str.strip().str.upper() == 'A'])
        data['tasa_calidad'] = round((c_a / t_cal * 100), 1) if t_cal > 0 else 0
    else:
        data['tasa_calidad'] = 0

    # OUTBOUND
    data['total_pedidos'] = df_surtido['docto_id'].nunique() if not df_surtido.empty else 0
    data['piezas_surtidas'] = float(df_surtido['cantidad_surtida'].sum()) if not df_surtido.empty else 0
    data['total_pedida'] = float(df_surtido['cantidad_pedida'].sum()) if not df_surtido.empty else 0
    data['tarimas_despachadas'] = float(df_surtido['tarimas'].sum()) if not df_surtido.empty else 0
    data['fill_rate'] = round((data['piezas_surtidas'] / data['total_pedida'] * 100), 1) if data['total_pedida'] > 0 else 0
    
    if not df_surtido.empty:
        valid_est = df_surtido[df_surtido['estado'].astype(str).str.strip() != '']
        t_est = len(valid_est)
        c_est = len(valid_est[valid_est['estado'].astype(str).str.strip().str.upper().isin(['SURTIDO', 'COMPLETO', 'COMPLETADO', 'CLOSED', 'CERRADO', 'FINALIZADO'])])
        data['pct_completados'] = round((c_est / t_est * 100), 1) if t_est > 0 else 0
    else:
        data['pct_completados'] = 0

    # PREV
    if not df_entradas_prev.empty:
        p_c = df_entradas_prev[df_entradas_prev['calidad'].astype(str).str.strip() != '']
        c_a_p = len(p_c[p_c['calidad'].astype(str).str.strip().str.upper() == 'A'])
        data['tasa_calidad_prev'] = round((c_a_p / len(p_c) * 100), 1) if len(p_c) > 0 else "N/A"
    else: data['tasa_calidad_prev'] = "N/A"
    
    if not df_surtido_prev.empty:
        t_p_p = df_surtido_prev['cantidad_pedida'].sum()
        t_s_p = df_surtido_prev['cantidad_surtida'].sum()
        data['fill_rate_prev'] = round((t_s_p / t_p_p * 100), 1) if t_p_p > 0 else "N/A"
        
        p_e = df_surtido_prev[df_surtido_prev['estado'].astype(str).str.strip() != '']
        c_p_e = len(p_e[p_e['estado'].astype(str).str.strip().str.upper().isin(['SURTIDO', 'COMPLETO', 'COMPLETADO', 'CLOSED', 'CERRADO', 'FINALIZADO'])])
        data['pct_completados_prev'] = round((c_p_e / len(p_e) * 100), 1) if len(p_e) > 0 else "N/A"
    else:
        data['fill_rate_prev'] = "N/A"
        data['pct_completados_prev'] = "N/A"

    # AI
    if start_date is None:
        if not df_entradas_ai.empty:
            a_c = df_entradas_ai[df_entradas_ai['calidad'].astype(str).str.strip() != '']
            a_a = len(a_c[a_c['calidad'].astype(str).str.strip().str.upper() == 'A'])
            data['tasa_calidad_ai'] = round((a_a / len(a_c) * 100), 1) if len(a_c) > 0 else 0
        else: data['tasa_calidad_ai'] = 0
            
        if not df_surtido_ai.empty:
            a_p = df_surtido_ai['cantidad_pedida'].sum()
            a_s = df_surtido_ai['cantidad_surtida'].sum()
            data['fill_rate_ai'] = round((a_s / a_p * 100), 1) if a_p > 0 else 0
            
            a_e = df_surtido_ai[df_surtido_ai['estado'].astype(str).str.strip() != '']
            a_c_e = len(a_e[a_e['estado'].astype(str).str.strip().str.upper().isin(['SURTIDO', 'COMPLETO', 'COMPLETADO', 'CLOSED', 'CERRADO', 'FINALIZADO'])])
            data['pct_completados_ai'] = round((a_c_e / len(a_e) * 100), 1) if len(a_e) > 0 else 0
        else:
            data['fill_rate_ai'] = 0; data['pct_completados_ai'] = 0
        
        data['total_pedidos_ai'] = df_surtido_ai['docto_id'].nunique()
        data['total_recibos_ai'] = df_entradas_ai['docto_id'].nunique()
    else:
        for k in ['tasa_calidad', 'fill_rate', 'pct_completados', 'total_pedidos', 'total_recibos']:
            data[f'{k}_ai'] = data[k]

    # Time Update
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            import pytz
            CDMX_TZ_LOCAL = pytz.timezone('America/Mexico_City')
            last_sync_res = conn.execute(text('SELECT "timestamp" FROM audit_logs WHERE event_type = \'SYNC\' ORDER BY "timestamp" DESC LIMIT 1')).fetchone()
            if last_sync_res:
                db_time = last_sync_res[0]
                if db_time.tzinfo is None: db_time = pytz.utc.localize(db_time)
                data['last_update'] = db_time.astimezone(CDMX_TZ_LOCAL).strftime('%d/%m/%Y %H:%M')
            else:
                data['last_update'] = datetime.now(CDMX_TZ_LOCAL).strftime('%d/%m/%Y %H:%M')
    except:
        CDMX_TZ_LOCAL = pytz.timezone('America/Mexico_City')
        data['last_update'] = datetime.now(CDMX_TZ_LOCAL).strftime('%d/%m/%Y %H:%M')

    # DATA / TABLES
    disp_ent = df_entradas.sort_values(['fecha_dt', 'docto_id'], ascending=[False, False])
    disp_sur = df_surtido.sort_values(['fecha', 'hora', 'docto_id'], ascending=[False, False, False], na_position='last')
    
    c_e = ['docto_id', 'referencia', 'fecha', 'sku', 'descripcion', 'cantidad', 'calidad', 'tarimas']
    c_s = ['docto_id', 'referencia', 'fecha', 'hora', 'cantidad_pedida', 'cantidad_surtida', 'tarimas', 'estado', 'fill_rate']
    
    data['entradas_data'] = disp_ent.head(50)[c_e].fillna('').to_dict(orient='records')
    data['entradas_full_history'] = disp_ent[c_e].fillna('').to_dict(orient='records')
    data['surtido_data'] = disp_sur.head(50)[c_s].fillna('').to_dict(orient='records')
    data['surtido_full_history'] = disp_sur[c_s].fillna('').to_dict(orient='records')

    # CHARTS
    if not df_entradas.empty:
        c_ent = df_entradas.groupby('fecha_dt').agg(total=('docto_id', 'nunique'), cantidad=('cantidad', 'sum')).reset_index()
        c_ent = c_ent.rename(columns={'fecha_dt': 'dia'}).sort_values('dia')
        c_ent['dia'] = c_ent['dia'].astype(str)
        data['chart_entradas'] = c_ent.to_dict(orient='records')
        
        skus = df_entradas[df_entradas['sku'].astype(str).str.strip() != ''].copy()
        skus['desc'] = skus['descripcion'].replace('', pd.NA).fillna(skus['sku'])
        if not skus.empty:
            c_skus = skus.groupby('desc')['cantidad'].sum().reset_index().rename(columns={'desc': 'descripcion', 'cantidad': 'total'})
            data['chart_skus'] = c_skus.sort_values('total', ascending=False).head(10).to_dict(orient='records')
        else: data['chart_skus'] = []
            
        cal = df_entradas[df_entradas['calidad'].astype(str).str.strip() != ''].copy()
        cal['tipo'] = cal['calidad'].str.strip().str.upper()
        if not cal.empty:
            c_cal = cal.groupby('tipo').size().reset_index(name='total').sort_values('total', ascending=False)
            data['chart_calidad'] = c_cal.to_dict(orient='records')
        else: data['chart_calidad'] = []
            
        tin = df_entradas.groupby('fecha_dt')['tarimas'].sum().reset_index().rename(columns={'fecha_dt': 'dia', 'tarimas': 'total'}).sort_values('dia')
        tin['dia'] = tin['dia'].astype(str)
        data['chart_tarimas_in'] = tin.to_dict(orient='records')
    else:
        data['chart_entradas'] = []; data['chart_skus'] = []; data['chart_calidad'] = []; data['chart_tarimas_in'] = []

    if not df_surtido.empty:
        cout = df_surtido.groupby('fecha_dt').agg(total=('docto_id', 'nunique'), cantidad=('cantidad_surtida', 'sum')).reset_index()
        cout = cout.rename(columns={'fecha_dt': 'dia'}).sort_values('dia')
        cout['dia'] = cout['dia'].astype(str)
        data['chart_surtido'] = cout.to_dict(orient='records')
        
        tout = df_surtido.groupby('fecha_dt')['tarimas'].sum().reset_index().rename(columns={'fecha_dt': 'dia', 'tarimas': 'total'}).sort_values('dia')
        tout['dia'] = tout['dia'].astype(str)
        data['chart_tarimas_out'] = tout.to_dict(orient='records')
        
        est = df_surtido.copy()
        est['estado_upper'] = est['estado'].astype(str).str.strip().str.upper().replace('', 'SIN ESTADO')
        cest = est.groupby('estado_upper').size().reset_index(name='total').rename(columns={'estado_upper': 'estado'}).sort_values('total', ascending=False)
        data['chart_estado'] = cest.to_dict(orient='records')
        
        def map_fr(fr):
            if pd.isna(fr): return None
            if fr >= 100: return '100%'
            elif fr >= 90: return '90-99%'
            elif fr >= 70: return '70-89%'
            elif fr >= 50: return '50-69%'
            else: return '<50%'
        
        fr = df_surtido.copy()
        fr['rango'] = fr['fill_rate'].apply(map_fr)
        fr = fr.dropna(subset=['rango'])
        if not fr.empty:
            cfr = fr.groupby('rango').agg(total=('rango', 'count'), min_fr=('fill_rate', 'min')).reset_index()
            data['chart_fillrate'] = cfr.sort_values('min_fr', ascending=False).to_dict(orient='records')
        else: data['chart_fillrate'] = []
    else:
        data['chart_surtido'] = []; data['chart_tarimas_out'] = []; data['chart_estado'] = []; data['chart_fillrate'] = []

    return data

# ====== REFRESH LOGIC (ADMIN ONLY) ======
# Obtenemos el rol del usuario para control de visualización
user_role = st.session_state.user.get("role", "user").lower() if "user" in st.session_state else "user"

# Bloque movido abajo


# ====== FILTERS ======
with st.sidebar:
    st.markdown("### 📅 Filtros de Tiempo")
    periodo = st.selectbox(
        "Seleccionar Período",
        ["Hoy", "Ayer", "Esta Semana", "Últimos 7 días", "Este Mes", "Mes Pasado", "Este Año", "Todo", "Rango Personalizado"],
        index=7 # Default to "Todo"
    )
    
    start_date = None
    end_date = None
    today = datetime.now().date()
    
    if periodo == "Hoy":
        start_date = today
        end_date = today
    elif periodo == "Ayer":
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
    elif periodo == "Esta Semana":
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif periodo == "Últimos 7 días":
        start_date = today - timedelta(days=7)
        end_date = today
    elif periodo == "Este Mes":
        start_date = today.replace(day=1)
        end_date = today
    elif periodo == "Mes Pasado":
        last_month = today.replace(day=1) - timedelta(days=1)
        start_date = last_month.replace(day=1)
        end_date = last_month
    elif periodo == "Este Año":
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif periodo == "Rango Personalizado":
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            start_date = st.date_input("Desde", today - timedelta(days=30))
        with col_f2:
            end_date = st.date_input("Hasta", today)
    else: # Todo
        start_date = None
        end_date = None

    # ====== REFRESH BUTTON (SECURED) ======
    st.divider()
    user_role = st.session_state.user.get("role", "user").lower()
    if user_role in ["admin", "gerencia", "moderador", "moderador_reebok"]:
        st.markdown("### 🔄 Sincronización")
        can_run, wait_time = get_cooldown_status(15)
        
        if st.session_state.get("force_sync_reebok", False):
            can_run = True
            
        if not can_run:
            st.warning(f"Sincronización reciente. Espera {wait_time} min para actualizar de nuevo.")
            if st.button("🔄 Forzar Actualización", help="Usa solo si es crítico"):
                st.session_state.force_sync_reebok = True
                st.rerun()
        
        if can_run:
            if st.button("🚀 Actualizar Datos WMS", use_container_width=True):
                st.session_state.force_sync_reebok = False
                status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_status.json")
                try:
                    with open(status_file, "w") as f:
                        json.dump({"message": "Iniciando...", "percent": 0, "status": "starting"}, f)
                except: pass

                try:
                    scraper_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wms_scraper.py")
                    env = os.environ.copy()
                    env["TRIGGERED_BY"] = st.session_state.user.get("email", "Unknown")
                    process = subprocess.Popen([sys.executable, scraper_script], shell=False, env=env)
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    while process.poll() is None:
                        try:
                            if os.path.exists(status_file):
                                with open(status_file, "r") as f:
                                    sd = json.load(f)
                                    pct = sd.get("percent", 0)
                                    progress_bar.progress(pct)
                                    status_text.info(f"Bot 1: {sd.get('message', '')} ({pct}%)")
                                    if sd.get("status") == "complete": break
                        except: pass
                        time.sleep(1)
                    process.wait()

                    if process.returncode == 0:
                        status_text.success("Bot 1 OK. Iniciando Bot 2...")
                        time.sleep(1)
                        finalizados_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wms_scraper_embarcados.py")
                        process2 = subprocess.Popen([sys.executable, finalizados_script], shell=False, env=env)
                        
                        while process2.poll() is None:
                            try:
                                if os.path.exists(status_file):
                                    with open(status_file, "r") as f:
                                        sd = json.load(f)
                                        pct = sd.get("percent", 0)
                                        progress_bar.progress(pct)
                                        status_text.info(f"Bot 2: {sd.get('message', '')} ({pct}%)")
                                        if sd.get("status") == "complete": break
                            except: pass
                            time.sleep(1)
                        process2.wait()

                        if process2.returncode == 0:
                            status_text.info("Unificando datos...")
                            unificador_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unificador.py")
                            subprocess.run([sys.executable, unificador_script], shell=False, env=env)
                            
                            save_last_run_now()
                            fetch_raw_data_from_db.clear()
                            fetch_raw_data_from_db.clear()
                            load_all_data_filtered.clear()
                            clear_ai_cache()
                            st.success("¡Datos actualizados con éxito!")
                            time.sleep(2)
                            st.rerun()
                        else: st.error("Error en Bot 2")
                    else: st.error("Error en Bot 1")
                except Exception as e: st.error(f"Error: {e}")
    else:
        st.info("💡 Los datos se actualizan automáticamente cada 30 minutos. Solo administradores pueden forzar actualización.")

# We pass last modified time to ensure unique cache key if file changed externally
try:
    # DB_PATH is not defined in the original script but used here? 
    # Actually, the original used DB_PATH which was missing a definition or using BASE_DIR logic.
    # Looking at line 40, it uses os.path.join(BASE_DIR, "data", "wms_data.db")
    DB_PATH_LOCAL = os.path.join(BASE_DIR, "data", "wms_data.db")
    db_mtime = os.path.getmtime(DB_PATH_LOCAL)
except:
    db_mtime = 0
    
app_data = load_all_data_filtered(start_date, end_date, db_mtime)

# Display Last Update Prominently

col_text, col_btn = st.columns([7, 3])
with col_text:
    st.markdown(f"<div style='margin-top: 15px; color: rgba(255,255,255,0.5); font-size: 0.85em;'><strong>Última Actualización:</strong> {app_data['last_update']} (Los datos se actualizan automáticamente o vía administrador)</div>", unsafe_allow_html=True)

with col_btn:
    if user_role in ["admin", "gerencia"]:
        can_run, wait_time = get_cooldown_status(15)
        
        if st.session_state.get("force_sync_reebok", False):
            can_run = True
            
        if not can_run:
            st.info(f"⏳ Sync bloqueado por 15 min. Faltan {wait_time} min.")
            if st.button("🔄 Forzar Sincronización", help="Usar solo si hay datos nuevos en WMS"):
                st.session_state.force_sync_reebok = True
                st.rerun()
        
        if can_run:
            if st.button("🔄 Sincronizar con Supabase"):
                st.session_state.force_sync_reebok = False
                status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_status.json")
                try:
                    with open(status_file, "w") as f:
                        json.dump({"message": "Iniciando...", "percent": 0, "status": "starting"}, f)
                except: pass

                try:
                    scraper_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wms_scraper.py")
                    env = os.environ.copy()
                    env["TRIGGERED_BY"] = st.session_state.user.get("email", "Unknown")
                    process = subprocess.Popen([sys.executable, scraper_script], shell=False, env=env)
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    while process.poll() is None:
                        try:
                            if os.path.exists(status_file):
                                with open(status_file, "r") as f:
                                    sd = json.load(f)
                                    pct = sd.get("percent", 0)
                                    progress_bar.progress(pct)
                                    status_text.info(f"Bot 1: {sd.get('message', '')} ({pct}%)")
                                    if sd.get("status") == "complete": break
                        except: pass
                        time.sleep(1)
                    process.wait()

                    if process.returncode == 0:
                        status_text.success("Fase 1 OK. Iniciando Fase 2...")
                        time.sleep(1)
                        finalizados_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wms_scraper_embarcados.py")
                        process2 = subprocess.Popen([sys.executable, finalizados_script], shell=False, env=env)
                        
                        while process2.poll() is None:
                            try:
                                if os.path.exists(status_file):
                                    with open(status_file, "r") as f:
                                        sd = json.load(f)
                                        pct = sd.get("percent", 0)
                                        progress_bar.progress(pct)
                                        status_text.info(f"Bot 2: {sd.get('message', '')} ({pct}%)")
                                        if sd.get("status") == "complete": break
                            except: pass
                            time.sleep(1)
                        process2.wait()

                        if process2.returncode == 0:
                            status_text.info("Unificando datos...")
                            unificador_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unificador.py")
                            subprocess.run([sys.executable, unificador_script], shell=False, env=env)
                            
                            save_last_run_now()
                            fetch_raw_data_from_db.clear()
                            fetch_raw_data_from_db.clear()
                            load_all_data_filtered.clear()
                            clear_ai_cache()
                            st.success("¡Datos actualizados con éxito!")
                            time.sleep(2)
                            st.rerun()
                        else: st.error("Error en Fase 2")
                    else: st.error("Error en Fase 1")
                except Exception as e: st.error(f"Error: {e}")



# ====== OPERATIONAL DASHBOARD (HTML) ======

# ====== LOAD EXTERNAL ASSETS ======
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

try:
    with open(os.path.join(ASSETS_DIR, 'reebok_style.css'), 'r', encoding='utf-8') as f:
        css_content = f.read()
    with open(os.path.join(ASSETS_DIR, 'reebok_dashboard.js'), 'r', encoding='utf-8') as f:
        js_content = f.read()
except Exception as e:
    st.error(f"Error loading Reebok assets: {e}")
    css_content = ""
    js_content = ""

# ====== INJECT DATA INTO JS ======

# Custom encoder for Decimal types (Postgres)
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        import decimal
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

js_content = js_content.replace('/*REEBOK_KPI_DATA_PLACEHOLDER*/ {}', json.dumps({
    'total_recibos': app_data['total_recibos'],
    'piezas_recibidas': app_data['piezas_recibidas'],
    'skus_unicos': app_data['skus_unicos'],
    'tarimas_recibidas': app_data['tarimas_recibidas'],
    'tasa_calidad': app_data['tasa_calidad'],
    'total_pedidos': app_data['total_pedidos'],
    'piezas_surtidas': app_data['piezas_surtidas'],
    'total_pedida': app_data['total_pedida'],
    'fill_rate': app_data['fill_rate'],
    'tarimas_despachadas': app_data['tarimas_despachadas'],
    'pct_completados': app_data['pct_completados'],
    'last_update': app_data['last_update']
}, cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_ENTRADAS_PLACEHOLDER*/[]', json.dumps(app_data['entradas_data'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_SURTIDO_PLACEHOLDER*/[]', json.dumps(app_data['surtido_data'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_ENTRADAS_FULL_PLACEHOLDER*/[]', json.dumps(app_data['entradas_full_history'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_SURTIDO_FULL_PLACEHOLDER*/[]', json.dumps(app_data['surtido_full_history'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_CHART_ENTRADAS_PLACEHOLDER*/[]', json.dumps(app_data['chart_entradas'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_CHART_SURTIDO_PLACEHOLDER*/[]', json.dumps(app_data['chart_surtido'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_CHART_SKUS_PLACEHOLDER*/[]', json.dumps(app_data['chart_skus'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_CHART_CALIDAD_PLACEHOLDER*/[]', json.dumps(app_data['chart_calidad'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_CHART_TARIMAS_IN_PLACEHOLDER*/[]', json.dumps(app_data['chart_tarimas_in'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_CHART_TARIMAS_OUT_PLACEHOLDER*/[]', json.dumps(app_data['chart_tarimas_out'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_CHART_ESTADO_PLACEHOLDER*/[]', json.dumps(app_data['chart_estado'], cls=DecimalEncoder))
js_content = js_content.replace('/*REEBOK_CHART_FILLRATE_PLACEHOLDER*/[]', json.dumps(app_data['chart_fillrate'], cls=DecimalEncoder))

# --- GENERATE AI INSIGHTS ---
# Solo generar AI text para los KPIs de mayor impacto (ahorra tokens / evita texto innecesario)
# Determinar el nombre del periodo para el reporte de la IA
ai_periodo_str = "Últimos 7 días (vs semana anterior)" if periodo == "Todo" else periodo

ai_insights = {
    'calidad': get_ai_insight('cumpl_72h', {
        'Periodo_Analisis': ai_periodo_str,
        'Tasa_Actual': f"{app_data['tasa_calidad_ai']}%",
        'Tasa_Anterior_Comparativa': f"{app_data['tasa_calidad_prev']}%" if "N/A" not in str(app_data['tasa_calidad_prev']) else "Sin datos previos para comparar",
        'Total_Recibos': app_data['total_recibos_ai'],
        'Gap_Puntos': max(0, 95 - float(app_data['tasa_calidad_ai'] or 0))
    }), 
    'fillrate': get_ai_insight('pct_surtido', {
        'Periodo_Analisis': ai_periodo_str,
        'Fill_Rate_Actual': f"{app_data['fill_rate_ai']}%",
        'Fill_Rate_Anterior_Comparativa': f"{app_data['fill_rate_prev']}%" if "N/A" not in str(app_data['fill_rate_prev']) else "Sin datos previos para comparar",
        'Total_Pedidos': app_data['total_pedidos_ai'],
        'Gap_Puntos': max(0, 95 - float(app_data['fill_rate_ai'] or 0))
    }),
    'completados': get_ai_insight('pct_surtido', {
        'Periodo_Analisis': ai_periodo_str,
        'Porcentaje_Cierre_Actual': f"{app_data['pct_completados_ai']}%",
        'Porcentaje_Cierre_Anterior': f"{app_data['pct_completados_prev']}%" if "N/A" not in str(app_data['pct_completados_prev']) else "Sin datos previos para comparar",
        'Total_Pedidos': app_data['total_pedidos_ai'],
        'Gap_Puntos': max(0, 95 - float(app_data['pct_completados_ai'] or 0))
    })
}
js_content = js_content.replace('/*REEBOK_AI_INSIGHTS_PLACEHOLDER*/ {}', json.dumps(ai_insights, cls=DecimalEncoder))

# ====== HTML BODY ======
periodo_str = f"Período: {periodo}"
if periodo == "Rango Personalizado":
    periodo_str = f"Del {start_date} al {end_date}"

html_body = f"""
<body>

<div class="topbar">
    <div>
        <div class="header-title">⚡ Dashboard Reebok</div>
        <div class="header-sub">Panel de Control Operativo — 10 KPIs</div>
    </div>
    <div style="display:flex; gap:10px; align-items:center;">
        <span class="badge" style="background:#f0f9ff; color:#0369a1; border:1px solid #bae6fd; font-weight:600;">{periodo_str}</span>
        <span class="badge badge-time" id="lastUpdate">...</span>
        <span class="badge badge-live">● EN LÍNEA</span>
    </div>
</div>

<div class="container">

    <!-- INBOUND -->
    <div class="section-title inbound">📦 INBOUND — Entradas</div>
    <div class="grid-kpi">
        <div class="card" onclick="openModal('recibos')" data-accent="blue">
            <div class="card-header">
                <div class="card-title-group">
                    <div class="card-label">Total Recibos</div>
                    <div class="card-subtitle">Documentos de Entrada</div>
                </div>
                <div class="card-icon" style="background:rgba(59,130,246,0.15);color:var(--blue);">📋</div>
            </div>
            <div class="card-body">
                <div class="card-value text-neon-blue" id="kpi_recibos">—</div>
                <div class="trend-badge trend-up" id="trend_recibos">▲ 0%</div>
            </div>
            <div class="card-footer">Documentos únicos procesados</div>
        </div>
        <div class="card" onclick="openModal('piezas_in')" data-accent="indigo">
            <div class="card-header">
                <div class="card-title-group">
                    <div class="card-label">Piezas Recibidas</div>
                    <div class="card-subtitle">Volumen de Entrada</div>
                </div>
                <div class="card-icon" style="background:rgba(99,102,241,0.15);color:var(--indigo);">📦</div>
            </div>
            <div class="card-body">
                <div class="card-value text-neon-indigo" id="kpi_piezas_in">—</div>
                <div class="trend-badge trend-up" id="trend_piezas_in">▲ 0%</div>
            </div>
            <div class="card-footer">Unidades totales recibidas</div>
        </div>
        <div class="card" onclick="openModal('skus')" data-accent="purple">
            <div class="card-header">
                <div class="card-title-group">
                    <div class="card-label">SKUs Únicos</div>
                    <div class="card-subtitle">Maestro de Materiales</div>
                </div>
                <div class="card-icon" style="background:rgba(139,92,246,0.15);color:var(--purple);">🏷️</div>
            </div>
            <div class="card-body">
                <div class="card-value text-neon-purple" id="kpi_skus">—</div>
                <div class="trend-badge trend-up" id="trend_skus">▲ 0%</div>
            </div>
            <div class="card-footer">Productos diferentes recibidos</div>
        </div>
        <div class="card" onclick="openModal('tarimas_in')" data-accent="pink">
            <div class="card-header">
                <div class="card-title-group">
                    <div class="card-label">Tarimas Recibidas</div>
                    <div class="card-subtitle">Carga Paletizada In</div>
                </div>
                <div class="card-icon" style="background:rgba(236,72,153,0.15);color:var(--pink);">🎨</div>
            </div>
            <div class="card-body">
                <div class="card-value text-neon-pink" id="kpi_tarimas_in">—</div>
                <div class="trend-badge trend-up" id="trend_tarimas_in">▲ 0%</div>
            </div>
            <div class="card-footer">Pallets procesados en entrada</div>
        </div>
        <div class="card" onclick="openModal('calidad')" data-accent="green">
            <div class="card-header">
                <div class="card-title-group">
                    <div class="card-label">Tasa Calidad</div>
                    <div class="card-subtitle">Cumplimiento QA</div>
                </div>
                <div class="card-icon" style="background:rgba(16,185,129,0.15);color:var(--green);">✅</div>
            </div>
            <div class="card-body">
                <div class="card-value text-neon-green" id="kpi_calidad">—</div>
                <div class="trend-badge trend-up" id="trend_calidad">▲ 0%</div>
            </div>
            <div class="card-footer">% producto calificado como 'A'</div>
        </div>
    </div>

    <!-- OUTBOUND -->
    <div class="section-title outbound">📤 OUTBOUND — Surtido</div>
    <div class="grid-kpi">
        <div class="card" onclick="openModal('pedidos')" data-accent="green">
            <div class="card-header">
                <div class="card-title-group">
                    <div class="card-label">Total Pedidos</div>
                    <div class="card-subtitle">Órdenes de Cliente</div>
                </div>
                <div class="card-icon" style="background:rgba(16,185,129,0.15);color:var(--green);">📑</div>
            </div>
            <div class="card-body">
                <div class="card-value text-neon-green" id="kpi_pedidos">—</div>
                <div class="trend-badge trend-up" id="trend_pedidos">▲ 0%</div>
            </div>
            <div class="card-footer">Órdenes de salida procesadas</div>
        </div>
        <div class="card" onclick="openModal('piezas_out')" data-accent="teal">
            <div class="card-header">
                <div class="card-title-group">
                    <div class="card-label">Piezas Surtidas</div>
                    <div class="card-subtitle">Volumen de Salida</div>
                </div>
                <div class="card-icon" style="background:rgba(20,184,166,0.15);color:var(--teal);">📤</div>
            </div>
            <div class="card-body">
                <div class="card-value text-neon-teal" id="kpi_piezas_out">—</div>
                <div class="trend-badge trend-up" id="trend_piezas_out">▲ 0%</div>
            </div>
            <div class="card-footer">Unidades totales despachadas</div>
        </div>
        <div class="card" onclick="openModal('fillrate')" data-accent="blue">
            <div class="card-header">
                <div class="card-title-group">
                    <div class="card-label">Fill Rate</div>
                    <div class="card-subtitle">Tasa de Surtido</div>
                </div>
                <div class="card-icon" style="background:rgba(59,130,246,0.15);color:var(--blue);">🚀</div>
            </div>
            <div class="card-body">
                <div class="card-value text-neon-blue" id="kpi_fillrate">—</div>
                <div class="trend-badge trend-up" id="trend_fillrate">▲ 0%</div>
            </div>
            <div class="card-footer" id="kpi_fillrate_footer">Progreso del despacho</div>
        </div>
        <div class="card" onclick="openModal('tarimas_out')" data-accent="orange">
            <div class="card-header">
                <div class="card-title-group">
                    <div class="card-label">Tarimas Desp.</div>
                    <div class="card-subtitle">Carga Paletizada Out</div>
                </div>
                <div class="card-icon" style="background:rgba(245,158,11,0.15);color:var(--orange);">🚛</div>
            </div>
            <div class="card-body">
                <div class="card-value text-neon-orange" id="kpi_tarimas_out">—</div>
                <div class="trend-badge trend-up" id="trend_tarimas_out">▲ 0%</div>
            </div>
            <div class="card-footer">Pallets enviados a despacho</div>
        </div>
        <div class="card" onclick="openModal('completados')" data-accent="amber">
            <div class="card-header">
                <div class="card-title-group">
                    <div class="card-label">Completados</div>
                    <div class="card-subtitle">Cumplimiento Surtido</div>
                </div>
                <div class="card-icon" style="background:rgba(245,158,11,0.15);color:var(--amber);">🏁</div>
            </div>
            <div class="card-body">
                <div class="card-value text-neon-amber" id="kpi_completados">—</div>
                <div class="trend-badge trend-up" id="trend_completados">▲ 0%</div>
            </div>
            <div class="card-footer">Pedidos finalizados al 100%</div>
        </div>
    </div>

    <!-- INBOUND CHARTS -->
    <div class="section-title inbound">📊 Gráficos Inbound</div>
    <div class="grid-4">
        <div class="chart-box" onclick="openModal('chart_entradas')">
            <div class="chart-title">📦 Entradas por Día <span class="chart-subtitle">Volumen de Piezas Recibidas</span></div>
            <canvas id="chartEntradasDia" class="chart-canvas"></canvas>
        </div>
        <div class="chart-box" onclick="openModal('chart_skus')">
            <div class="chart-title">🏷️ Top 10 SKUs <span class="chart-subtitle">Artículos con mayor movimiento</span></div>
            <canvas id="chartSKUs" class="chart-canvas chart-canvas-circular"></canvas>
        </div>
        <div class="chart-box" onclick="openModal('chart_calidad')">
            <div class="chart-title">✅ Distribución de Calidad <span class="chart-subtitle">Estatus de Calidad Inbound</span></div>
            <canvas id="chartCalidad" class="chart-canvas chart-canvas-circular"></canvas>
        </div>
        <div class="chart-box" onclick="openModal('chart_tarimas_in')">
            <div class="chart-title">🎨 Tarimas por Día <span class="chart-subtitle">Paletizado Recibido</span></div>
            <canvas id="chartTarimasIn" class="chart-canvas"></canvas>
        </div>
    </div>

    <!-- OUTBOUND CHARTS -->
    <div class="section-title outbound">📊 Gráficos Outbound</div>
    <div class="grid-4">
        <div class="chart-box" onclick="openModal('chart_surtido')">
            <div class="chart-title">📤 Surtido por Día <span class="chart-subtitle">Eficacia de Despacho Diario</span></div>
            <canvas id="chartSurtidoDia" class="chart-canvas"></canvas>
        </div>
        <div class="chart-box" onclick="openModal('chart_fillrate')">
            <div class="chart-title">🎯 Distribución Fill Rate <span class="chart-subtitle">Nivel de cumplimiento de piezas</span></div>
            <canvas id="chartFillRate" class="chart-canvas"></canvas>
        </div>
        <div class="chart-box" onclick="openModal('chart_estado')">
            <div class="chart-title">🏁 Estado de Pedidos <span class="chart-subtitle">Pipeline de Órdenes</span></div>
            <canvas id="chartEstado" class="chart-canvas chart-canvas-circular"></canvas>
        </div>
        <div class="chart-box" onclick="openModal('chart_tarimas_out')">
            <div class="chart-title">🚛 Tarimas Despachadas <span class="chart-subtitle">Paletizado de Salida</span></div>
            <canvas id="chartTarimasOut" class="chart-canvas"></canvas>
        </div>
    </div>

</div>

<!-- MODAL -->
<div class="modal-overlay" id="modal" onclick="closeModal()">
    <div class="modal-box" onclick="event.stopPropagation()">
        <div class="modal-header">
            <h2 class="modal-title" id="modal-title">Detalle</h2>
            <div id="modal-actions"></div>
            <button class="modal-close" onclick="closeModal()">✕</button>
        </div>
        <div id="modal-summary"></div>
        <div style="overflow-x:auto; margin-top:1rem;">
            <table id="modal-table"></table>
        </div>
        <button class="modal-btn" onclick="closeModal()">Cerrar</button>
    </div>
</div>

</body>
"""

# ====== ASSEMBLE FINAL HTML ======
html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reebok WMS Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
""" + css_content + """
        /* DARK MODE OVERRIDES */
        :root {
            --bg: #0e1117 !important;
            --card: #161b22 !important;
            --text: #f0f6fc !important;
            --muted: #8b949e !important;
            --border: #30363d !important;
            --blue: #58a6ff !important;
            --indigo: #79c0ff !important;
            --purple: #d2a8ff !important;
            --pink: #ff7baf !important;
            --green: #3fb950 !important;
            --orange: #ffa657 !important;
            --teal: #39c5bb !important;
            --amber: #d29922 !important;
        }
        body { background: var(--bg) !important; color: var(--text) !important; }
        .topbar { background: #010409 !important; border-bottom: 1px solid var(--border) !important; color: #f0f6fc !important; }
        .header-title { color: #f0f6fc !important; }
        .header-sub, .card-subtitle, .card-footer, .chart-subtitle { color: var(--muted) !important; }
        .card, .chart-box { 
            background: var(--card) !important; 
            border: 1px solid var(--border) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        .card:hover[data-accent="blue"] { border-color: #3b82f6 !important; box-shadow: 0 8px 30px rgba(59, 130, 246, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="green"] { border-color: #10b981 !important; box-shadow: 0 8px 30px rgba(16, 185, 129, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="purple"] { border-color: #d2a8ff !important; box-shadow: 0 8px 30px rgba(210, 168, 255, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="indigo"] { border-color: #79c0ff !important; box-shadow: 0 8px 30px rgba(121, 192, 255, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="pink"] { border-color: #ff7baf !important; box-shadow: 0 8px 30px rgba(255, 123, 175, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="teal"] { border-color: #39c5bb !important; box-shadow: 0 8px 30px rgba(57, 197, 187, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="orange"] { border-color: #ffa657 !important; box-shadow: 0 8px 30px rgba(255, 166, 87, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="amber"] { border-color: #d29922 !important; box-shadow: 0 8px 30px rgba(210, 153, 34, 0.15) !important; transform: translateY(-3px) !important; }
        .chart-box:hover { border-color: var(--blue) !important; transform: translateY(-3px) !important; }
        .card-label { color: #f0f6fc !important; }
        .section-title { color: #f0f6fc !important; border-bottom-color: var(--border) !important; }
        .badge-time { background: #21262d !important; color: #c9d1d9 !important; border-color: var(--border) !important; }
        .modal-box { background: #161b22 !important; color: #f0f6fc !important; border: 1px solid var(--border) !important; }
        .modal-header { border-bottom-color: var(--border) !important; }
        .modal-close { color: var(--muted) !important; }
        .modal-close:hover { color: #f0f6fc !important; }
        .alert-item { background: #0d1117 !important; border-color: var(--border) !important; }

        /* NEON GRADIENTS - 2026 */
        .text-neon-blue { background: linear-gradient(135deg, #79c0ff, #58a6ff) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; text-shadow: 0 0 20px rgba(88, 166, 255, 0.3) !important; }
        .text-neon-green { background: linear-gradient(135deg, #56d364, #3fb950) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; text-shadow: 0 0 20px rgba(63, 185, 80, 0.3) !important; }
        .text-neon-purple { background: linear-gradient(135deg, #e3b8ff, #d2a8ff) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; text-shadow: 0 0 20px rgba(210, 168, 255, 0.3) !important; }
        .text-neon-indigo { background: linear-gradient(135deg, #a5d6ff, #79c0ff) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; text-shadow: 0 0 20px rgba(121, 192, 255, 0.3) !important; }
        .text-neon-pink { background: linear-gradient(135deg, #ff9bce, #ff7baf) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; text-shadow: 0 0 20px rgba(255, 123, 175, 0.3) !important; }
        .text-neon-teal { background: linear-gradient(135deg, #60e3d5, #39c5bb) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; text-shadow: 0 0 20px rgba(57, 197, 187, 0.3) !important; }
        .text-neon-orange { background: linear-gradient(135deg, #ffc282, #ffa657) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; text-shadow: 0 0 20px rgba(255, 166, 87, 0.3) !important; }
        .text-neon-amber { background: linear-gradient(135deg, #e3af35, #d29922) !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; text-shadow: 0 0 20px rgba(210, 153, 34, 0.3) !important; }
    </style>
</head>
""" + html_body + """
<script>
    /* CHART.JS DARK THEME DEFAULTS */
    if (typeof Chart !== 'undefined') {
        Chart.defaults.color = '#8b949e';
        Chart.defaults.borderColor = 'rgba(48, 54, 61, 0.5)';
        Chart.defaults.plugins.tooltip.backgroundColor = '#161b22';
        Chart.defaults.plugins.tooltip.titleColor = '#f0f6fc';
        Chart.defaults.plugins.tooltip.bodyColor = '#8b949e';
        Chart.defaults.plugins.tooltip.borderColor = '#30363d';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
    }
""" + js_content + """
</script>
</html>
"""

components.html(html_content, height=1000, scrolling=True)
