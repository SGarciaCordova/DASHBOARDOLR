import streamlit as st

# Persistir navegación en URL con ALIAS elegante
st.query_params["page"] = "arena"

# MANDATORY SECURITY CHECK: Protect the Leaderboard from direct access
user_data = st.session_state.get("user")
if not user_data:
    st.error("ACCESO DENEGADO. Por favor inicie sesión desde el HUB principal.")
    st.stop()
if user_data.get("role") != "admin":
    st.error("ACCESO DENEGADO. Módulo en prueba, acceso exclusivo para administradores.")
    st.stop()
import streamlit.components.v1 as components
import pandas as pd
import json
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text
from src.database import get_supabase_engine, upsert_desempeno_csv
import plotly.express as px
import plotly.graph_objects as go

# Marcar que estamos en el Leaderboard — Dashboard.py usa esto para restaurar la página

# Si viene una señal de refresh tras upload, limpiar caché
if st.session_state.pop('_refresh_leaderboard', False):
    st.cache_data.clear()

# Configuración Horaria
CDMX_TZ = pytz.timezone('America/Mexico_City')

# Deshabilitar menú default de Streamlit
st.markdown("""
<style>
    #MainMenu, footer, .stDeployButton { display: none !important; }
    .main { background-color: #0d1117; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load_data(start_date_str, end_date_str):
    engine = get_supabase_engine()
    if not engine:
        return pd.DataFrame()
    query = """
    SELECT * FROM "Desempeno_Op_" 
    WHERE DATE(fecha) >= :start AND DATE(fecha) <= :end
    AND usuario != 'uchavez'
    AND detalle = 'Salida por Defecto'
    """
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={"start": start_date_str, "end": end_date_str})
        if not df.empty:
            # Shift fix: Treat DB time as literal wall-clock time (No extra conversions)
            df['fecha'] = pd.to_datetime(df['fecha']).dt.tz_localize(None)
            df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0)
        return df
    except Exception as e:
        return pd.DataFrame()

# ================= FILTROS =================
now_cdmx = datetime.now(CDMX_TZ)
today = now_cdmx.date()

with st.sidebar:
    st.markdown("### ⚙️ Configuración Arena")
    period_mode = st.radio("Periodo:", options=["Hoy", "Ayer", "Esta Semana", "Este Mes", "Rango Fijo"], index=0)
    if period_mode == "Hoy": start_date, end_date = today, today
    elif period_mode == "Ayer": start_date = today - timedelta(days=1); end_date = start_date
    elif period_mode == "Esta Semana": start_date = today - timedelta(days=today.weekday()); end_date = today
    elif period_mode == "Este Mes": start_date = today.replace(day=1); end_date = today
    else:
        date_range = st.date_input("Rango Personalizado", value=(today - timedelta(days=7), today))
        if isinstance(date_range, tuple) and len(date_range) == 2: start_date, end_date = date_range
        else: start_date, end_date = today, today

    # ================= DATA UPLOAD =================
    st.markdown("---")
    st.markdown("### 📤 Actualizar Datos")
    with st.form("upload_form", clear_on_submit=False):
        uploaded_file = st.file_uploader(
            "Arrastra tu CSV del WMS aquí",
            type=["csv"],
            help="Sube el archivo OPERATIONS_BY_USER exportado del WMS. Los duplicados se detectan automáticamente."
        )
        submit_btn = st.form_submit_button("🚀 Procesar y subir", use_container_width=True, type="primary")
    
    if submit_btn and uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            st.markdown(f"""
            <div style="background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.3); 
                        border-radius: 10px; padding: 12px; margin: 8px 0;">
                <div style="font-size: 0.8rem; color: #8b949e; text-transform: uppercase; margin-bottom: 4px;">📎 Archivo detectado</div>
                <div style="font-weight: 700; color: #f0f6fc;">{uploaded_file.name}</div>
                <div style="color: #58a6ff; font-weight: 600;">{len(df_upload):,} registros en CSV</div>
                <div style="font-size: 0.75rem; color: #8b949e; margin-top: 4px;">Columnas: {', '.join(df_upload.columns[:6].tolist())}{'...' if len(df_upload.columns) > 6 else ''}</div>
            </div>
            """, unsafe_allow_html=True)
            
            total_rows = len(df_upload)
            progress_bar = st.progress(0, text=f"🔄 Conectando con la base de datos... ({total_rows:,} registros)")
            
            def update_progress(batch_num, total_batches):
                pct = batch_num / total_batches
                rows_done = min(batch_num * 5000, total_rows)
                progress_bar.progress(pct, text=f"🚀 Subiendo: {rows_done:,} / {total_rows:,} registros...")
            
            result = upsert_desempeno_csv(df_upload, progress_callback=update_progress)
            progress_bar.progress(1.0, text="✅ Upload completo")
            
            if result['errors'] == 0:
                st.markdown(f"""
                <div style="background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); 
                            border-radius: 10px; padding: 12px; margin: 8px 0;">
                    <div style="font-weight: 700; color: #4ade80; font-size: 1.1rem;">✅ Upload Exitoso</div>
                    <div style="display: flex; gap: 15px; margin-top: 8px;">
                        <div><span style="font-weight: 800; color: #4ade80; font-size: 1.3rem;">{result['inserted']}</span><br>
                             <span style="font-size: 0.7rem; color: #8b949e;">NUEVOS</span></div>
                        <div><span style="font-weight: 800; color: #f59e0b; font-size: 1.3rem;">{result['duplicates']}</span><br>
                             <span style="font-size: 0.7rem; color: #8b949e;">DUPLICADOS</span></div>
                        <div><span style="font-weight: 800; color: #58a6ff; font-size: 1.3rem;">{result['total_csv']}</span><br>
                             <span style="font-size: 0.7rem; color: #8b949e;">TOTAL CSV</span></div>
                    </div>
                    <div style="font-size: 0.75rem; color: #8b949e; margin-top: 8px;">⏱️ {now_cdmx.strftime('%H:%M')} CDMX</div>
                </div>
                """, unsafe_allow_html=True)
                load_data.clear()
                st.rerun()
            else:
                st.error(f"❌ Error: {result['error_msg']}")
                if result['inserted'] > 0:
                    st.warning(f"⚠️ Se insertaron {result['inserted']} registros antes del error.")
        except Exception as e:
            st.error(f"❌ Error leyendo CSV: {e}")
    elif submit_btn and uploaded_file is None:
        st.warning("⚠️ Selecciona un archivo CSV primero.")

df_raw = load_data(start_date.isoformat(), end_date.isoformat())

if df_raw.empty:
    st.info(f"No hay registros operativos para el periodo seleccionado.")
    st.stop()

# ================= PROCESAMIENTO =================
df = df_raw.copy().dropna(subset=['usuario'])

total_pzas_global = int(df['cantidad'].sum())
avg_pzas_hr_global = round(total_pzas_global / max(len(df['fecha'].dt.hour.unique()), 1), 1)
total_ops = df['usuario'].nunique()

# --- Cálculo de Inicio de Operación GLOBAL ---
df_dates = df.copy()
df_dates['solo_fecha'] = df_dates['fecha'].dt.date
daily_starts_global = df_dates.groupby('solo_fecha')['fecha'].min()

if start_date == end_date:
    if not daily_starts_global.empty:
        header_start_time = daily_starts_global.iloc[0].strftime('%H:%M')
    else: header_start_time = "--:--"
    label_start_time = "Primer Piqueo"
else:
    if not daily_starts_global.empty:
        secs = daily_starts_global.dt.hour * 3600 + daily_starts_global.dt.minute * 60 + daily_starts_global.dt.second
        avg_total_seconds = secs.mean()
        header_start_time = f"{int(avg_total_seconds // 3600):02d}:{int((avg_total_seconds % 3600) // 60):02d}"
    else: header_start_time = "--:--"
    label_start_time = "Inicio Promedio"

# Grouping for Peak Productivity
df['hora_int'] = df['fecha'].dt.hour
peak_df = df.groupby(['usuario', 'hora_int'])['cantidad'].sum().reset_index()
peak_indices = peak_df.groupby('usuario')['cantidad'].idxmax()
peak_hours = peak_df.loc[peak_indices][['usuario', 'hora_int']]

op_details = {}
for user in df['usuario'].unique():
    user_df = df[df['usuario'] == user]
    ref_summary = user_df.groupby('referencia')['cantidad'].sum().reset_index()
    ref_list = ref_summary.sort_values(by='cantidad', ascending=False).head(10).to_dict('records')
    
    # Peak hour for this specific user
    p_h = peak_hours[peak_hours['usuario'] == user]['hora_int'].iloc[0]
    peak_formatted = f"{p_h:02d}:00"
    
    # Inicios diarios para este usuario
    u_daily_starts = user_df.groupby(user_df['fecha'].dt.date)['fecha'].min()
    if start_date == end_date:
        f_op = u_daily_starts.iloc[0].strftime('%H:%M') if not u_daily_starts.empty else "--:--"
    else:
        if not u_daily_starts.empty:
            secs = u_daily_starts.dt.hour * 3600 + u_daily_starts.dt.minute * 60 + u_daily_starts.dt.second
            avg_s = secs.mean()
            f_op = f"{int(avg_s // 3600):02d}:{int((avg_s % 3600) // 60):02d}"
        else: f_op = "--:--"
    
    op_details[user] = {
        'usuario': user,
        'total_piezas': int(user_df['cantidad'].sum()),
        'tareas': int(len(user_df)),
        'skus': int(user_df['sku'].nunique()),
        'refs_sum': ref_list,
        'first_op': f_op,
        'last_op': user_df['fecha'].max().strftime('%H:%M'),
        'peak_hour': peak_formatted
    }

grouped = df.groupby('usuario').agg(
    total_piezas=('cantidad', 'sum'),
    tareas=('id', 'count'),
    skus_distintos=('sku', 'nunique'),
    pedidos=('referencia', 'nunique'),
    primer_registro=('fecha', 'min'),
    ultimo_registro=('fecha', 'max')
).reset_index()

grouped['piezas_por_pedido'] = (grouped['total_piezas'] / grouped['pedidos']).round(1)

# --- Nueva Lógica de Velocidad: Piezas / Horas con actividad (Man-Hours) ---
# Contamos cuántas 'slots' de hora distintos tuvo el usuario con actividad
df['fecha_hora_key'] = df['fecha'].dt.strftime('%Y-%m-%d %H')
user_active_hours = df.groupby('usuario')['fecha_hora_key'].nunique()

ranked = pd.merge(grouped, peak_hours, on='usuario', how='left')
# Mapear las horas activas al dataframe ranked
ranked['horas_man_hour'] = ranked['usuario'].map(user_active_hours).fillna(1)
ranked['vel_piezas_hr'] = (ranked['total_piezas'] / ranked['horas_man_hour']).round(1)

ranked = ranked.sort_values(by='total_piezas', ascending=False).reset_index(drop=True)
ranked['posicion'] = ranked.index + 1

top3 = ranked.head(3)
candidatos_vel = ranked[ranked['total_piezas'] >= 50]
r_flash = candidatos_vel.sort_values(by='vel_piezas_hr', ascending=False).iloc[0].to_dict() if not candidatos_vel.empty else ranked.sort_values(by='vel_piezas_hr', ascending=False).iloc[0].to_dict()
r_versatil = ranked.sort_values(by='skus_distintos', ascending=False).iloc[0].to_dict()
r_tareas = ranked.sort_values(by='tareas', ascending=False).iloc[0].to_dict()
r_pesado = ranked.sort_values(by='piezas_por_pedido', ascending=False).iloc[0].to_dict()

# ================= HTML / CSS / JS COMPONENT =================
html_template = """
<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0d1117; --card: #161b22; --border: #30363d; --gold: #fbbf24; --silver: #9ca3af; --bronze: #b45309; --blue: #58a6ff; --neon: #3b82f6; }
        body { background-color: transparent; font-family: 'Inter', sans-serif; color: #f0f6fc; margin: 0; padding: 0; overflow-x: hidden; }
        .arena-title { 
            text-align: center; 
            font-size: 3.8rem; 
            font-weight: 900; 
            background: linear-gradient(135deg, var(--gold), #fff, var(--gold));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 5px; 
            text-transform: uppercase; 
            letter-spacing: 5px;
            filter: drop-shadow(0 0 15px rgba(251, 191, 36, 0.6));
            animation: title-glow 3s infinite alternate;
        }
        @keyframes title-glow {
            from { filter: drop-shadow(0 0 10px rgba(251, 191, 36, 0.4)); }
            to { filter: drop-shadow(0 0 25px rgba(251, 191, 36, 0.8)); }
        }
        .arena-subtitle { text-align: center; color: #8b949e; font-size: 0.9rem; margin-bottom: 2.5rem; text-transform: uppercase; letter-spacing: 2px; font-weight: 500; }
        .date-highlight { color: var(--blue); text-shadow: 0 0 8px rgba(59, 130, 246, 0.8); border: 1px solid rgba(59, 130, 246, 0.3); padding: 4px 15px; border-radius: 20px; background: rgba(59, 130, 246, 0.05); display: inline-block; }
        .pulse-row { display: flex; justify-content: center; gap: 15px; margin-bottom: 2.5rem; flex-wrap: wrap; }
        .pulse-card { background: linear-gradient(145deg, #1c2128, #161b22); border: 1px solid var(--border); border-radius: 10px; padding: 8px 15px; text-align: center; min-width: 130px; box-shadow: 0 0 8px rgba(59, 130, 246, 0.05); position: relative; overflow: hidden; }
        .pulse-val { font-size: 1.3rem; font-weight: 900; color: var(--blue); margin-bottom: 2px; display: block; }
        .pulse-lbl { font-size: 0.55rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
        .podium-container { display: flex; justify-content: center; align-items: flex-end; gap: 20px; margin-bottom: 3rem; height: 380px; }
        .podium-card { background: var(--card); border: 2px solid var(--border); border-radius: 16px 16px 8px 8px; padding: 20px 10px; text-align: center; width: 230px; transition: all 0.4s ease; cursor: pointer; position: relative; }
        .podium-card:hover { transform: translateY(-12px) scale(1.03); filter: brightness(1.2); z-index: 10; }
        .podium-1 { height: 340px; border-color: var(--gold); box-shadow: 0 0 15px rgba(251, 191, 36, 0.25); }
        .podium-1:hover { box-shadow: 0 0 45px rgba(251, 191, 36, 0.8), inset 0 0 15px rgba(251, 191, 36, 0.2); border-color: #fde047; }
        .podium-2 { height: 280px; border-color: var(--silver); box-shadow: 0 0 15px rgba(156, 163, 175, 0.2); }
        .podium-2:hover { box-shadow: 0 0 45px rgba(156, 163, 175, 0.8), inset 0 0 15px rgba(156, 163, 175, 0.2); border-color: #f3f4f6; }
        .podium-3 { height: 240px; border-color: var(--bronze); box-shadow: 0 0 15px rgba(180, 83, 9, 0.2); }
        .podium-3:hover { box-shadow: 0 0 45px rgba(180, 83, 9, 0.8), inset 0 0 15px rgba(180, 83, 9, 0.2); border-color: #d97706; }
        .medal-icon { font-size: 3.5rem; margin-top: -45px; margin-bottom: 5px; display: block; filter: drop-shadow(0 0 10px rgba(255,255,255,0.2)); }
        .op-name { font-size: 1.4rem; font-weight: 800; margin-bottom: 2px; text-transform: uppercase; color: #fff; }
        .op-score { font-size: 2.2rem; font-weight: 900; margin-bottom: 2px; line-height: 1; }
        .score-1 { color: var(--gold); text-shadow: 0 0 15px rgba(251, 191, 36, 0.5); }
        .score-2 { color: var(--silver); text-shadow: 0 0 15px rgba(156, 163, 175, 0.4); }
        .score-3 { color: var(--bronze); text-shadow: 0 0 15px rgba(180, 83, 9, 0.4); }
        
        .podium-peak { 
            font-size: 0.75rem; 
            color: var(--gold); 
            margin-bottom: 12px; 
            background: rgba(251,191,36,0.08);
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-weight: 700;
            border: 1px solid rgba(251,191,36,0.2);
            text-transform: uppercase;
        }

        .podium-stats { margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.08); display: flex; justify-content: space-around; gap: 8px; }
        .p-stat { display: flex; flex-direction: column; }
        .p-stat-val { font-weight: 700; color: var(--blue); font-size: 1.1rem; }
        .p-stat-lbl { font-size: 0.65rem; color: #8b949e; text-transform: uppercase; }
        .badges-container { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; padding: 0 10px; }
        .badge-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 15px; text-align: center; min-width: 200px; margin-bottom: 15px; transition: all 0.3s ease; cursor: pointer; }
        .badge-card:hover { transform: scale(1.05); box-shadow: 0 0 25px rgba(59, 130, 246, 0.3); border-color: var(--blue); }
        .b-vel { border-bottom: 4px solid #ef4444; }
        .b-ver { border-bottom: 4px solid #8b5cf6; }
        .b-lin { border-bottom: 4px solid #06b6d4; }
        .b-pes { border-bottom: 4px solid #10b981; }
        .badge-title { font-size: 0.8rem; color: #8b949e; text-transform: uppercase; margin-bottom: 5px; }
        .badge-icon { font-size: 2rem; margin-bottom: 10px; }
        .badge-user { font-size: 1.1rem; font-weight: 700; color: #f0f6fc; }
        .badge-val { font-size: 0.9rem; color: var(--blue); font-weight: 600; }
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0, 0, 0, 0.9); backdrop-filter: blur(12px); display: none; justify-content: center; align-items: center; z-index: 1000; }
        .modal-box { background: #1c2128; border: 1px solid var(--blue); box-shadow: 0 0 60px rgba(59, 130, 246, 0.5); border-radius: 20px; width: 520px; max-width: 90%; padding: 35px; position: relative; animation: modalIn 0.3s forwards cubic-bezier(0.4, 0, 0.2, 1); }
        .modal-close { position: absolute; top: 25px; right: 25px; font-size: 28px; cursor: pointer; color: #8b949e; }
        .modal-title { font-size: 2.2rem; font-weight: 900; color: var(--blue); margin-bottom: 15px; text-transform: uppercase; border-bottom: 1px solid var(--border); padding-bottom: 12px; }
        .modal-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 25px 0; }
        .ms-card { background: rgba(255,255,255,0.04); padding: 12px; border-radius: 10px; text-align: center; border: 1px solid rgba(255,255,255,0.03); }
        .ms-val { font-size: 1.6rem; font-weight: 800; display: block; color: #fff; }
        .ms-lbl { font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
        .ref-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 0.95rem; }
        .ref-id { color: #8b949e; } .ref-val { font-weight: 700; color: var(--gold); }

        /* Chart Styles */
        .chart-card { 
            background: rgba(22, 27, 34, 0.6); 
            border: 1px solid var(--border); 
            border-radius: 16px; 
            padding: 16px 20px; 
            margin: 20px auto; 
            max-width: 98%; 
            backdrop-filter: blur(10px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            box-sizing: border-box;
        }
        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .chart-title {
            font-size: 1.1rem;
            font-weight: 800;
            color: #f0f6fc;
            text-transform: uppercase;
            letter-spacing: 2px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .chart-title i { color: var(--neon); }
        .chart-legend {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.75rem;
            color: #8b949e;
        }
        .legend-color {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="arena-title">OPERATOR RANKED <br><span style="font-size: 1.5rem; font-weight: bold; color: #ff4d4d; text-shadow: 0 0 10px rgba(255, 77, 77, 0.8);">v.1.1</span></div>
    <div class="arena-subtitle">REALTIME WORKFORCE ANALYTICS | <span class="date-highlight">START_DATE - END_DATE</span></div>
    
    <div class="podium-container">
        <div class="podium-card podium-2" style="display: SHOW_P2" onclick="openModal('USER_P2')">
            <span class="medal-icon">🥈</span>
            <div class="op-name">USER_P2</div>
            <div class="podium-peak">⚡ Pico: PEAK_P2</div>
            <div class="op-score score-2">PIEZAS_P2</div>
            <span class="op-metric">Pzas Surtidas</span>
            <div class="podium-stats">
                <div class="p-stat"><span class="p-stat-val">PEDS_P2</span><span class="p-stat-lbl">Pedidos</span></div>
                <div class="p-stat"><span class="p-stat-val">VEL_P2</span><span class="p-stat-lbl">P/Hr</span></div>
                <div class="p-stat"><span class="p-stat-val">FIRST_P2</span><span class="p-stat-lbl">Inicio</span></div>
            </div>
        </div>
        <div class="podium-card podium-1" style="display: SHOW_P1" onclick="openModal('USER_P1')">
            <span class="medal-icon">👑</span>
            <div class="op-name">USER_P1</div>
            <div class="podium-peak">⚡ Pico: PEAK_P1</div>
            <div class="op-score score-1">PIEZAS_P1</div>
            <span class="op-metric">Pzas Surtidas</span>
            <div class="podium-stats">
                <div class="p-stat"><span class="p-stat-val">PEDS_P1</span><span class="p-stat-lbl">Pedidos</span></div>
                <div class="p-stat"><span class="p-stat-val">VEL_P1</span><span class="p-stat-lbl">P/Hr</span></div>
                <div class="p-stat"><span class="p-stat-val">FIRST_P1</span><span class="p-stat-lbl">Inicio</span></div>
            </div>
        </div>
        <div class="podium-card podium-3" style="display: SHOW_P3" onclick="openModal('USER_P3')">
            <span class="medal-icon">🥉</span>
            <div class="op-name">USER_P3</div>
            <div class="podium-peak">⚡ Pico: PEAK_P3</div>
            <div class="op-score score-3">PIEZAS_P3</div>
            <span class="op-metric">Pzas Surtidas</span>
            <div class="podium-stats">
                <div class="p-stat"><span class="p-stat-val">PEDS_P3</span><span class="p-stat-lbl">Pedidos</span></div>
                <div class="p-stat"><span class="p-stat-val">VEL_P3</span><span class="p-stat-lbl">P/Hr</span></div>
                <div class="p-stat"><span class="p-stat-val">FIRST_P3</span><span class="p-stat-lbl">Inicio</span></div>
            </div>
        </div>
    </div>

    <div class="pulse-row">
        <div class="pulse-card" style="border-color: var(--blue);"><span class="pulse-val">FIRST_PICK_VAL</span><span class="pulse-lbl">FIRST_PICK_LBL</span></div>
        <div class="pulse-card"><span class="pulse-val">TOTAL_PZAS</span><span class="pulse-lbl">Piezas en Arena</span></div>
        <div class="pulse-card"><span class="pulse-val">AVG_VEL</span><span class="pulse-lbl">Pzas / Hora Ø</span></div>
        <div class="pulse-card"><span class="pulse-val">TOTAL_OPS</span><span class="pulse-lbl">Operadores</span></div>
    </div>

    <div class="badges-container">
        <div class="badge-card b-vel" onclick="openModal('USER_FLASH')">
            <div class="badge-title">El Más Veloz</div>
            <div class="badge-icon">⚡</div>
            <div class="badge-user">USER_FLASH</div>
            <div class="badge-val">VEL_FLASH Pzas/Hr</div>
        </div>
        <div class="badge-card b-ver" onclick="openModal('USER_VERS')">
            <div class="badge-title">Diversidad SKUs</div>
            <div class="badge-icon">🧠</div>
            <div class="badge-user">USER_VERS</div>
            <div class="badge-val">SKUS_VERS SKUs Únicos</div>
        </div>
        <div class="badge-card b-lin" onclick="openModal('USER_TARS')">
            <div class="badge-title">Maestro de Tareas</div>
            <div class="badge-icon">📠</div>
            <div class="badge-user">USER_TARS</div>
            <div class="badge-val">VAL_TARS Tareas</div>
        </div>
        <div class="badge-card b-pes" onclick="openModal('USER_PESO')">
            <div class="badge-title">Peso Pesado</div>
            <div class="badge-icon">🏗️</div>
            <div class="badge-user">USER_PESO</div>
            <div class="badge-val">PESO_PESO Pzas/Pedido</div>
        </div>
    </div>
    <div class="modal-overlay" id="overlay" onclick="closeModal()">
        <div class="modal-box" onclick="event.stopPropagation()">
            <span class="modal-close" onclick="closeModal()">×</span>
            <div class="modal-title" id="mUser">USUARIO</div>
            <div class="modal-stats">
                <div class="ms-card"><span class="ms-val" id="mPzas">0</span><span class="ms-lbl">Total Piezas</span></div>
                <div class="ms-card"><span class="ms-val" id="mTars">0</span><span class="ms-lbl">Tareas Realizadas</span></div>
                <div class="ms-card"><span class="ms-val" id="mSkus">0</span><span class="ms-lbl">SKUs Distintos</span></div>
                <div class="ms-card"><span class="ms-val" id="mTime">0</span><span class="ms-lbl">Jornada Activa</span></div>
            </div>
            <div style="font-weight: 700; color: #8b949e; font-size: 0.8rem; margin: 25px 0 10px 0; text-transform: uppercase;">Top Pedidos</div>
            <div id="mRefsList"></div>
        </div>
    </div>

    <!-- Efficiency Chart Section -->
    <div class="chart-card">
        <div class="chart-header">
            <div class="chart-title">
                <span>🚀 Perfil de Eficiencia Horaria (Top 5)</span>
            </div>
        </div>
        <div style="height: 300px; position: relative;">
            <canvas id="efficiencyChart"></canvas>
        </div>
    </div>
    <script>
        const details = DETAILS_JSON;
        const chartData = CHART_DATA_JSON;

        function openModal(user) {
            const data = details[user]; if(!data) return;
            document.getElementById('mUser').innerText = data.usuario;
            document.getElementById('mPzas').innerText = data.total_piezas.toLocaleString();
            document.getElementById('mTars').innerText = data.tareas;
            document.getElementById('mSkus').innerText = data.skus;
            document.getElementById('mTime').innerText = data.first_op + ' - ' + data.last_op;
            let html = '';
            data.refs_sum.forEach(r => { html += `<div class="ref-row"><span class="ref-id">Pedido: ${r.referencia}</span><span class="ref-val">${r.cantidad} pzas</span></div>`; });
            document.getElementById('mRefsList').innerHTML = html;
            document.getElementById('overlay').style.display = 'flex';
        }

        function closeModal() { document.getElementById('overlay').style.display = 'none'; }

        // Initialize Chart
        function initChart() {
            const ctx = document.getElementById('efficiencyChart').getContext('2d');
            
            const colors = [
                { border: '#fbbf24', bg: 'rgba(251, 191, 36, 0.1)' }, // Gold
                { border: '#9ca3af', bg: 'rgba(156, 163, 175, 0.1)' }, // Silver
                { border: '#b45309', bg: 'rgba(180, 83, 9, 0.1)' },  // Bronze
                { border: '#58a6ff', bg: 'rgba(88, 166, 255, 0.1)' }, // Blue
                { border: '#3fb950', bg: 'rgba(63, 185, 80, 0.1)' }   // Green
            ];

            const datasets = chartData.users.map((user, i) => {
                const color = colors[i % colors.length];
                return {
                    label: user.name,
                    data: user.data,
                    borderColor: color.border,
                    backgroundColor: color.border, // Points use the border color
                    fill: false, // Clean look, no messy overlaps
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 3,
                    pointBackgroundColor: color.border,
                    pointBorderColor: '#0d1117',
                    pointBorderWidth: 1,
                    pointHoverRadius: 6,
                    pointHoverBorderWidth: 3
                };
            });

            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {
                        padding: {
                            bottom: 5,
                            left: 0,
                            right: 15,
                            top: 0
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index',
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            align: 'end',
                            labels: {
                                color: '#8b949e',
                                usePointStyle: true,
                                padding: 20,
                                font: {
                                    family: "'Inter', sans-serif",
                                    size: 11,
                                    weight: '600'
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: '#1c2128',
                            titleColor: '#58a6ff',
                            bodyColor: '#f0f6fc',
                            borderColor: '#30363d',
                            borderWidth: 1,
                            padding: 16,
                            boxPadding: 10,
                            bodySpacing: 10,
                            titleMarginBottom: 12,
                            usePointStyle: true,
                            bodyFont: {
                                family: "'Inter', sans-serif",
                                size: 12
                            },
                            callbacks: {
                                label: function(context) {
                                    return ` ${context.dataset.label}: ${context.parsed.y} pzas`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: '#f0f6fc', 
                                font: { 
                                    size: 13, 
                                    weight: '700' 
                                },
                                autoSkip: true,
                                maxRotation: 0,
                                minRotation: 0
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#f0f6fc',
                                font: { 
                                    size: 13, 
                                    weight: '700' 
                                },
                                callback: function(value) {
                                    return value;
                                }
                            }
                        }
                    }
                }
            });
        }

        window.onload = initChart;
    </script>
</body>
</html>
"""

# --- Preparación de Datos para Chart.js ---
top5_names = ranked.head(5)['usuario'].tolist()
df_top5 = df[df['usuario'].isin(top5_names)].copy()
df_top5['hora'] = df_top5['fecha'].dt.hour
df_top5['dia'] = df_top5['fecha'].dt.date
num_days = max(df_top5['dia'].nunique(), 1)

hourly_stats = df_top5.groupby(['hora', 'usuario'])['cantidad'].sum().reset_index()
if num_days > 1:
    hourly_stats['cantidad'] = (hourly_stats['cantidad'] / num_days).round(1)

min_h, max_h = int(df['fecha'].dt.hour.min()), int(df['fecha'].dt.hour.max())
all_hours_list = list(range(min_h, max_h + 1))
template_df = pd.MultiIndex.from_product([all_hours_list, top5_names], names=['hora', 'usuario']).to_frame(index=False)
hourly_full = pd.merge(template_df, hourly_stats, on=['hora', 'usuario'], how='left').fillna(0)

chart_data_js = {
    'labels': [f"{h:02d}:00" for h in all_hours_list],
    'users': []
}
for user in top5_names:
    user_vals = hourly_full[hourly_full['usuario'] == user]['cantidad'].tolist()
    chart_data_js['users'].append({
        'name': user,
        'data': user_vals
    })

# Inyección
html_final = html_template.replace("START_DATE", start_date.strftime("%d %b")).replace("END_DATE", end_date.strftime("%d %b %Y")) \
    .replace("TOTAL_PZAS", f"{total_pzas_global:,}").replace("AVG_VEL", str(avg_pzas_hr_global)).replace("TOTAL_OPS", str(total_ops)) \
    .replace("FIRST_PICK_VAL", header_start_time).replace("FIRST_PICK_LBL", label_start_time) \
    .replace("DETAILS_JSON", json.dumps(op_details)) \
    .replace("CHART_DATA_JSON", json.dumps(chart_data_js))

for idx, p_key in enumerate(["P1", "P2", "P3"]):
    if idx < len(top3):
        p_d = top3.iloc[idx]
        u = p_d['usuario']
        html_final = html_final.replace(f"SHOW_{p_key}", "block").replace(f"USER_{p_key}", u).replace(f"PEAK_{p_key}", op_details[u]['peak_hour']) \
            .replace(f"PIEZAS_{p_key}", f"{int(p_d['total_piezas']):,}").replace(f"PEDS_{p_key}", str(int(p_d['pedidos']))).replace(f"VEL_{p_key}", str(p_d['vel_piezas_hr'])) \
            .replace(f"FIRST_{p_key}", op_details[u]['first_op'])
    else: html_final = html_final.replace(f"SHOW_{p_key}", "none")

html_final = html_final.replace("USER_FLASH", r_flash['usuario']).replace("VEL_FLASH", str(r_flash['vel_piezas_hr'])) \
    .replace("USER_VERS", r_versatil['usuario']).replace("SKUS_VERS", str(int(r_versatil['skus_distintos']))) \
    .replace("USER_TARS", r_tareas['usuario']).replace("VAL_TARS", str(int(r_tareas['tareas']))) \
    .replace("USER_PESO", r_pesado['usuario']).replace("PESO_PESO", str(r_pesado['piezas_por_pedido']))

components.html(html_final, height=1350)

st.divider()
# --- Incluir Inicio en Tabla Ranked ---
ranked['inicio'] = ranked['usuario'].apply(lambda x: op_details[x]['first_op'])
st.dataframe(ranked[['posicion', 'usuario', 'inicio', 'total_piezas', 'pedidos', 'skus_distintos', 'vel_piezas_hr', 'piezas_por_pedido']].rename(columns={'posicion':'Rank','usuario':'Operador','inicio':'Inicio','total_piezas':'Piezas','pedidos':'Pedidos','skus_distintos':'SKUs','vel_piezas_hr':'Pzas/Hr','piezas_por_pedido':'Pzas/Pedido'}), hide_index=True, use_container_width=True)
st.markdown("<div style='text-align: center; color: #6c757d; font-size: 0.8rem; margin-top: 2rem;'>OPERATIONAL ANALYTICS HUB | DESIGNED BY SERGIO CORDOVA © 2026</div>", unsafe_allow_html=True)
