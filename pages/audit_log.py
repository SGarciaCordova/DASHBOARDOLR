import streamlit as st

# Persistir navegación en URL para que F5 regrese aquí
_active_page = "pages/audit_log.py"
st.session_state["_active_page"] = _active_page
st.query_params["page"] = _active_page
import pandas as pd
from datetime import datetime, timedelta, timezone
from src.database import get_supabase_engine
from sqlalchemy import text
import pytz

# Configuración Horaria
CDMX_TZ = pytz.timezone('America/Mexico_City')

# No set_page_config here if it's called via st.Page (it inherits from Dashboard.py usually, 
# but st.Page documentation says it's better to NOT have it in the subpages or it might error if already set)
# Actually, st.Page handles the title and icon.

# --- Permissions Check ---
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Por favor inicia sesión.")
    st.stop()

if st.session_state.user.get("role") != "admin":
    st.error("🚫 Acceso denegado: Se requieren permisos de Administrador.")
    st.stop()

st.title("🛡️ Registro de Actividad (Audit Log)")

engine = get_supabase_engine()

@st.cache_data(ttl=60)
def get_audit_data():
    if not engine:
        st.error("Configuración de base de datos no encontrada (DATABASE_URL).")
        return pd.DataFrame()
    try:
        query = "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 2000"
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"Error al cargar logs: {e}")
        return pd.DataFrame()

df = get_audit_data()

if df.empty:
    st.info("No hay registros de actividad aún.")
    st.stop()
else:
    st.sidebar.caption(f"Total de registros en DB: {len(df)}")

df['timestamp'] = pd.to_datetime(df['timestamp'])
# Aseguramos que el timestamp sea interpretado como UTC (de Supabase) y convertido a CDMX
if df['timestamp'].dt.tz is None:
    df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert(CDMX_TZ)
else:
    df['timestamp'] = df['timestamp'].dt.tz_convert(CDMX_TZ)

# --- Summary Cards & Online Stats ---
now_cdmx = datetime.now(CDMX_TZ)
today = now_cdmx.date()

# 1. Usuarios Online (Humanos - Últimos 15 minutos)
# Filtramos identidades de bots/scrapers
def is_bot(email):
    bots = ['REEBOK_UNIFIER', 'REEBOK_SCRAPER', 'REEBOK_SCRAPER_AIRPORT', 'UNKNOWN', '_SCRAPER', '_UNIFIER', 'SISTEMA_']
    if not email: return True
    return any(b.upper() in str(email).upper() for b in bots)

threshold_online = now_cdmx - timedelta(minutes=15)
recent_activity = df[df['timestamp'] > threshold_online]
online_users_list = [u for u in recent_activity['user_email'].unique() if not is_bot(u)]
online_count = len(online_users_list)


# 2. Otros KPIs
events_today = len(df[df['timestamp'].dt.date == today])
active_24h_df = df[df['timestamp'] > (now_cdmx - timedelta(hours=24))]
active_users_24h = len([u for u in active_24h_df['user_email'].unique() if not is_bot(u)])

scraper_errors = len(df[
    (df['event_type'] == 'SCRAPER_ERROR') | (df['status'] == 'ERROR')
])


last_sync_row = df[df['event_type'] == 'SYNC'].iloc[0] if 'SYNC' in df['event_type'].values else None
last_sync_time = last_sync_row['timestamp'].strftime("%H:%M:%S") if last_sync_row is not None else "N/A"

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Eventos Hoy", events_today)
with c2:
    st.metric("Usuarios (24h)", active_users_24h)
with c3:
    st.metric("Usuarios Online", online_count)
    if online_count > 0:
        with st.popover("👥 Ver quiénes"):
            for u in online_users_list:
                st.write(f"- {u}")
    else:
        st.caption("Sin actividad reciente")
with c4:
    st.metric("Errores Detectados", scraper_errors)
with c5:
    st.metric("Última Sincronización", last_sync_time)

st.divider()

# --- Filters ---
with st.expander("🔍 Filtros de Búsqueda", expanded=True):
    f1, f2, f3, f4 = st.columns(4)
    search = f1.text_input("Búsqueda por texto (detalle)", placeholder="Escribe para buscar...")
    
    event_list = ["Todos", "LOGIN", "LOGOUT", "SCRAPER_RUN", "SCRAPER_ERROR", "SYNC", "PERMISSION_CHANGE", "EXPORT"]
    e_type = f2.selectbox("Tipo de Evento", event_list)
    
    user_list = ["Todos"] + sorted(df['user_email'].dropna().unique().tolist())
    u_filter = f3.selectbox("Usuario", user_list)
    
    # Range of dates
    date_range = f4.date_input("Rango de fechas", [today - timedelta(days=7), today])

# Apply filters
filtered_df = df.copy()
if search:
    filtered_df = filtered_df[filtered_df['detail'].str.contains(search, case=False, na=False)]
if e_type != "Todos":
    filtered_df = filtered_df[filtered_df['event_type'] == e_type]
if u_filter != "Todos":
    filtered_df = filtered_df[filtered_df['user_email'] == u_filter]
if isinstance(date_range, (list, tuple)):
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[(filtered_df['timestamp'].dt.date >= start_date) & 
                                 (filtered_df['timestamp'].dt.date <= end_date)]
    elif len(date_range) == 1:
        start_date = date_range[0]
        filtered_df = filtered_df[filtered_df['timestamp'].dt.date == start_date]

# --- Helper for Colors ---
COLOR_MAP = {
    "LOGIN": "🔵 LOGIN",
    "LOGOUT": "⚪ LOGOUT",
    "SCRAPER_RUN": "🟠 SCRAPER_RUN",
    "SCRAPER_ERROR": "🔴 SCRAPER_ERROR",
    "SYNC": "🟢 SYNC",
    "PERMISSION_CHANGE": "💗 PERMISSION",
    "EXPORT": "🟡 EXPORT"
}

# Map status icons
filtered_df['status_display'] = filtered_df['status'].apply(lambda x: "✅ OK" if x == "OK" else "❌ ERR")
# Map event types to include emoji/color reference
filtered_df['event_display'] = filtered_df['event_type'].apply(lambda x: COLOR_MAP.get(x, f"⚪ {x}"))

st.write(f"Mostrando **{len(filtered_df)}** registros")

# --- Table ---
st.dataframe(
    filtered_df[['timestamp', 'user_email', 'event_display', 'detail', 'ip_address', 'status_display']],
    column_config={
        "timestamp": st.column_config.DatetimeColumn("Fecha/Hora", format="DD/MM/YYYY HH:mm:ss"),
        "user_email": "Usuario",
        "event_display": "Evento",
        "detail": "Detalle",
        "ip_address": "IP",
        "status_display": "Estado"
    },
    use_container_width=True,
    hide_index=True
)

if st.button("🔄 Refrescar Datos"):
    st.cache_data.clear()
    st.rerun()
