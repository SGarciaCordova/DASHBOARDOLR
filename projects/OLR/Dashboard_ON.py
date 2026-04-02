import streamlit as st
import streamlit.components.v1 as components
import json
import numpy as np
import base64
import os
import io
import pandas as pd
import src.data_loader as data_loader
import src.kpi_engine as kpi_engine
import src.alert_engine as alert_engine
import src.ml_predictor as ml_predictor
from src.database import log_activity
import src.ai_summarizer as ai_summarizer
import pytz

st.set_page_config(page_title="OLR Mesa de Control", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# Configuración Horaria
CDMX_TZ = pytz.timezone('America/Mexico_City')

# Persistent MENU button + hide Streamlit chrome
# Hide Streamlit chrome but keep Header (Sidebar Toggle) visible
st.markdown("""
<style>
    #MainMenu, footer, .stDeployButton { display: none !important; }
</style>
""", unsafe_allow_html=True)

# Function to get base64 of logo
def get_base64_logo():
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

logo_b64 = get_base64_logo()

# Load data from Google Sheets
sheet_name = "REPORTE MR 2026 RICARDO"
df_entradas_raw, df_surtidos_raw, is_mock = data_loader.load_data(sheet_name)

# ====== DATE FILTER (Sidebar) ======
from datetime import datetime, date, timedelta
import calendar

with st.sidebar:
    # st.markdown("### 📅 Filtro de Fecha") # Removed header as Expander serves as header
    
    now_cdmx = datetime.now(CDMX_TZ)
    today = now_cdmx.date()
    start_date, end_date = None, None
    filter_mode = "General (Todo)" # Default

    # Filter Expander (The "Bar" the user clicks)
    with st.expander("📅 Filtros de Periodo / Configuración", expanded=False):
        col1, col2 = st.columns([1, 1])
        with col1:
            filter_mode = st.radio(
                "Modo de Filtro:",
                options=["General (Todo)", "Mes Específico", "Rango Manual"],
                index=0,
                horizontal=True
            )

        with col2:
            if filter_mode == "General (Todo)":
                st.info("Vista General: Comparando vs Semana Anterior")
                start_date, end_date = None, None

            elif filter_mode == "Mes Específico":
                months = {
                    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
                    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
                }
                # Default to current month
                sel_month_name = st.selectbox("Seleccionar Mes:", list(months.values()), index=today.month-1)
                sel_year = st.number_input("Año:", min_value=2023, max_value=2030, value=today.year)
                
                # Month logic
                month_num = list(months.keys())[list(months.values()).index(sel_month_name)]
                import calendar
                last_day = calendar.monthrange(sel_year, month_num)[1]
                start_date = date(sel_year, month_num, 1)
                end_date = date(sel_year, month_num, last_day)
                st.success(f"Filtrando: {sel_month_name} {sel_year}")

            else: # Rango Manual
                default_start = date(today.year, 1, 1)
                date_range = st.date_input(
                    "Seleccionar periodo:",
                    value=(default_start, today),
                    format="DD/MM/YYYY"
                )
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                    st.info(f"Mostrando: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")

    # Apply Date Filter Logic
    if start_date and end_date:
        df_entradas = kpi_engine.filter_by_custom_dates(df_entradas_raw, 'FECHA DE LLEGADA', start_date, end_date)
        df_surtidos = kpi_engine.filter_by_custom_dates(df_surtidos_raw, 'FECHA A ENTREGAR', start_date, end_date)
    else:
        # General View
        df_entradas = df_entradas_raw
        df_surtidos = df_surtidos_raw

# ====== EXPORT DATA (Sidebar) ======
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📥 Exportar Datos")
    
    # Generate Excel in memory
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_entradas.to_excel(writer, sheet_name='ENTRADAS', index=False)
        df_surtidos.to_excel(writer, sheet_name='SURTIDOS', index=False)
    
    st.download_button(
        label="⬇️ Descargar Excel",
        data=buffer,
        file_name=f"Data_Dashboard_{datetime.now(CDMX_TZ).date()}.xlsx",
        mime="application/vnd.ms-excel",
        on_click=lambda: log_activity(st.session_state.user['email'], "EXPORT", "Exportación de reporte OLR (Excel)")
    )

# ====== PREVIOUS PERIOD KPIs (for WoW Change) ======
# Determine comparison baseline based on filter
# If Month Filter -> Compare vs Previous Month
# If General/Week -> Compare vs Previous Week (Standard WoW)
if start_date and end_date and filter_mode == "Mes Específico":
    comp_period = 'month'
    comp_ref = start_date
    wow_label = "vs Mes Ant."
else:
    comp_period = 'week'
    comp_ref = date.today()
    wow_label = "vs Sem. Ant."

df_entradas_prev = kpi_engine.get_previous_period_data(df_entradas_raw, 'FECHA DE LLEGADA', period=comp_period, ref_date=comp_ref)
df_surtidos_prev = kpi_engine.get_previous_period_data(df_surtidos_raw, 'FECHA A ENTREGAR', period=comp_period, ref_date=comp_ref)

# ====== CALCULATE VALID COUNTS (filter blanks) ======
# Entradas: count rows with valid PEDIMENTO
entradas_validas = len(df_entradas[df_entradas['PEDIMENTO'].notna() & (df_entradas['PEDIMENTO'] != '')]) if 'PEDIMENTO' in df_entradas.columns else len(df_entradas)

# Surtidos: count rows with TOTAL DE PIEZAS > 0
surtidos_df_temp = df_surtidos.copy()
surtidos_df_temp['total_temp'] = kpi_engine.clean_numeric(surtidos_df_temp, 'TOTAL DE PIEZAS')
surtidos_validos = len(surtidos_df_temp[surtidos_df_temp['total_temp'] > 0])

# ====== INBOUND KPIs ======
cumpl_72h = kpi_engine.get_cumplimiento_72h(df_entradas)
tiempo_ing = kpi_engine.get_tiempo_ingreso(df_entradas)
vol_recib = kpi_engine.get_volumen_recibido(df_entradas)
carga_op = kpi_engine.get_carga_operativa(df_entradas) # moved to bonus/secondary
tiempo_extra = kpi_engine.get_tiempo_extra_indicador(df_entradas) # Kept as quality/sl breach
efic_desc = kpi_engine.get_eficiencia_descarga(df_entradas)

# ====== OUTBOUND KPIs ======
cumpl_entrega = kpi_engine.get_cumplimiento_entrega(df_surtidos) # OTIF
pct_surtido = kpi_engine.get_pct_surtido(df_surtidos) # Fill Rate
audit_quality = kpi_engine.get_audit_quality(df_surtidos) # New
vol_surtido = kpi_engine.get_volumen_surtido(df_surtidos)
avance_etapa = kpi_engine.get_avance_etapa(df_surtidos) # Pipeline/Process Completeness
backlog = kpi_engine.get_backlog(df_surtidos)
desemp_cliente = kpi_engine.get_desempeno_cliente(df_surtidos)

# ====== PREVIOUS PERIOD KPIs (for WoW Change) ======
cumpl_72h_prev = kpi_engine.get_cumplimiento_72h(df_entradas_prev)
cumpl_entrega_prev = kpi_engine.get_cumplimiento_entrega(df_surtidos_prev)
audit_quality_prev = kpi_engine.get_audit_quality(df_surtidos_prev)

# Calculate WoW changes
wow_sla = kpi_engine.calculate_wow_change(cumpl_72h['pct'], cumpl_72h_prev['pct'])
wow_otif = kpi_engine.calculate_wow_change(cumpl_entrega['pct'], cumpl_entrega_prev['pct'])
wow_fulfillment = kpi_engine.calculate_wow_change(audit_quality['pct'], audit_quality_prev['pct'])

# ====== ML RISK PREDICTION ======
risk_prediction = ml_predictor.predict_sla_risk(df_entradas)

# ====== CHART DATA ======
trend_df = kpi_engine.get_lead_time_by_week(df_entradas)
weekly_df = kpi_engine.get_weekly_throughput(df_surtidos)
comp_chart = kpi_engine.get_compliance_detail(df_entradas)
vol_df = kpi_engine.get_volume_by_type(df_entradas)
status_df = kpi_engine.get_status_distribution(df_surtidos)
client_df = kpi_engine.get_orders_by_client(df_surtidos)
pipeline_df = kpi_engine.get_pipeline_funnel(df_surtidos)
wip_metrics = kpi_engine.get_wip_metrics(df_surtidos)

# Prepare all data for JavaScript
all_kpis = {
    'cumpl_72h': cumpl_72h,
    'cumpl_72h': cumpl_72h,
    'tiempo_ing': tiempo_ing,
    'vol_recib': vol_recib,
    'carga_op': carga_op.to_dict('records') if not carga_op.empty else [],
    'tiempo_extra': tiempo_extra,
    'efic_desc': efic_desc,
    'pct_surtido': pct_surtido,
    'avance_etapa': avance_etapa,
    'cumpl_entrega': cumpl_entrega,
    'audit_quality': audit_quality,
    'backlog': backlog,
    'wip_metrics': wip_metrics,
    'vol_surtido': vol_surtido,
    'desemp_cliente': desemp_cliente.head(10).to_dict('records') if not desemp_cliente.empty else [],
    'trend_data': trend_df.to_dict('records') if not trend_df.empty else [],
    'weekly_data': weekly_df.to_dict('records') if not weekly_df.empty else [],
    'comp_chart': comp_chart.to_dict('records') if not comp_chart.empty else [],
    'vol_data': vol_df.to_dict('records') if not vol_df.empty else [],
    'status_data': status_df.to_dict('records') if not status_df.empty else [],
    'client_data': client_df.head(5).to_dict('records') if not client_df.empty else [],
    'pipeline_data': pipeline_df.to_dict('records') if not pipeline_df.empty else [],
    'entradas_count': entradas_validas,
    'surtidos_count': surtidos_validos,
    'is_connected': not is_mock,
    # WoW Changes
    'wow': {
        'sla': wow_sla,
        'otif': wow_otif,
        'fulfillment': wow_fulfillment
    },
    # ML Risk Prediction
    'risk_prediction': risk_prediction,
    'ai_insights': {
        'vol_surtido': ai_summarizer.get_ai_insight('vol_surtido', vol_surtido),
        'cumpl_72h': ai_summarizer.get_ai_insight('cumpl_72h', cumpl_72h)
    }
}

# ====== GENERATE ALERTS ======
current_kpis = {'cumpl_72h': cumpl_72h, 'cumpl_entrega': cumpl_entrega, 'audit_quality': audit_quality}
previous_kpis = {'cumpl_72h': cumpl_72h_prev, 'cumpl_entrega': cumpl_entrega_prev, 'audit_quality': audit_quality_prev}
alerts_data = alert_engine.generate_alerts(df_entradas, df_surtidos, current_kpis, previous_kpis)
# Debug alerts (remove later)
# print(f"DEBUG: alerts_data keys: {list(alerts_data.keys())}") 
all_kpis['alerts'] = alerts_data

def sanitize(obj):
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize(i) for i in obj]
    elif isinstance(obj, (np.int64, np.int32, np.int_)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.floating)):
        return 0 if obj != obj else float(obj)
    elif isinstance(obj, float) and (obj != obj):
        return 0
    return obj

all_kpis = sanitize(all_kpis)

# Pillar / WoW logic
def render_pill(value, label):
    if value is None or (isinstance(value, float) and value != value):
        return ""
    if value == 0:
        return f'<span class="wow-change wow-neutral" title="{label}">─ 0.0%</span>'
    cls = "wow-up" if value > 0 else "wow-down"
    icon = "▲" if value > 0 else "▼"
    return f'<span class="wow-change {cls}" title="{label}">{icon} {abs(value):.1f}%</span>'

# Load External Assets
try:
    with open('assets/style.css', 'r', encoding='utf-8') as f:
        css_content = f.read()
    with open('assets/dashboard.js', 'r', encoding='utf-8') as f:
        js_content = f.read()
except Exception as e:
    st.error(f"Error loading assets: {e}")
    css_content = ""
    js_content = ""

# Inject Data into JS
# We replace the placeholders with actual JSON data
js_content = js_content.replace('/*KPI_DATA_PLACEHOLDER*/ {}', json.dumps(all_kpis))
js_content = js_content.replace('/*STATUS_COLORS_PLACEHOLDER*/ {}', json.dumps({
    'ENTREGADO': '#10b981',
    'LISTO PARA EMBARQUE': '#f59e0b',
    'EN PROCESO': '#3b82f6',
    'PENDIENTE': '#9ca3af'
}))

# Construct HTML Body (Dynamic)
html_body = f"""
<body>
<div class="topbar">
    <div class="logo-section">
        <img src="data:image/png;base64,{logo_b64}" class="header-logo">
        <div class="header-text">
            <h1>Dashboard ON</h1>
            <div class="signature">by Sergio Cordova</div>
        </div>
    </div>
</div>

<div class="main-scroll-area">
    <div class="status-bar {'connected' if not is_mock else 'demo'}">
        <span>{'✓ <strong>CONECTADO</strong> a Google Sheets' if not is_mock else '⚠️ <strong>MODO DEMO</strong>'} | 
        Entradas: {entradas_validas} | Surtidos: {surtidos_validos}</span>
        
        <!-- Red Notification Badge Trigger -->
        <div class="notification-trigger" onclick="showModal('notifications')">
            🔔 Notificaciones
            {f'<span class="badge">{alerts_data.get("total_count", 0)}</span>' if alerts_data.get("total_count", 0) > 0 else ''}
        </div>
    </div>
    
    <div class="container">
        <div class="section-title">Inbound (Entradas)</div>
    <div class="grid-6">
        <div class="card" onclick="showModal('cumpl_72h')" data-accent="green">
            <div class="card-header"><div class="card-label">SLA Compliance 72h<span class="card-sub">Cumplimiento de SLA</span></div><div class="card-icon" style="background:rgba(16,185,129,0.15);">⏰</div></div>
            <div class="card-value text-neon-green">{cumpl_72h['pct']:.1f}%{render_pill(wow_sla, wow_label)}</div>
            <div class="card-change">{cumpl_72h['cumple']}/{cumpl_72h['total']} on time</div>
        </div>
        <div class="card" onclick="showModal('tiempo_ing')" data-accent="orange">
            <div class="card-header"><div class="card-label">Dock to Stock Time<span class="card-sub">Tiempo de Ingreso</span></div><div class="card-icon" style="background:rgba(245,158,11,0.15);">⏱️</div></div>
            <div class="card-value text-neon-orange">{tiempo_ing['promedio']:.1f}d</div>
            <div class="card-change">Avg Days (Promedio)</div>
        </div>
        <div class="card" onclick="showModal('vol_recib')" data-accent="purple">
            <div class="card-header"><div class="card-label">Inbound Volume<span class="card-sub">Volumen de Entrada</span></div><div class="card-icon" style="background:rgba(139,92,246,0.15);">📦</div></div>
            <div class="card-value text-neon-purple">{vol_recib['piezas']:,.0f}</div>
            <div class="card-change">{vol_recib['cajas']:,.0f} boxes (cajas)</div>
        </div>
        <div class="card" onclick="showModal('tiempo_extra')" data-accent="red">
            <div class="card-header"><div class="card-label">SLA Breach (Overtime)<span class="card-sub">Tiempo Excedido</span></div><div class="card-icon" style="background:rgba(239,68,68,0.15);">⚠️</div></div>
            <div class="card-value text-neon-red">{tiempo_extra['excedidos']}</div>
            <div class="card-change">{tiempo_extra['pct_excedido']:.1f}% breach rate</div>
        </div>
        <div class="card" onclick="showModal('efic_desc')" data-accent="cyan">
            <div class="card-header"><div class="card-label">Unloading Efficiency<span class="card-sub">Eficiencia Descarga</span></div><div class="card-icon" style="background:rgba(6,182,212,0.15);">🚛</div></div>
            <div class="card-value text-neon-cyan">{efic_desc['eficiencia']:.1f}%</div>
            <div class="card-change">{efic_desc['en_meta']} within target</div>
        </div>
        <div class="card" onclick="showModal('risk_prediction')" data-accent="red">
            <div class="card-header">
                <div class="card-label">SLA Inbound Risk<span class="card-sub">Riesgo Incumplimiento 72h</span></div>
                <div class="card-icon" style="background:rgba(239,68,68,0.15);">📥</div>
            </div>
            <div class="card-value text-neon-red">{risk_prediction.get('high_risk_count', 0)}</div>
            <div class="card-change">Pedimentos en riesgo de exceder SLA</div>
        </div>
    </div>
    
    <div class="section-title">📤 Outbound (Surtidos)</div>
    <div class="grid-6">
        <div class="card" onclick="showModal('cumpl_entrega')" data-accent="green">
            <div class="card-header"><div class="card-label">OTIF (On Time In Full)<span class="card-sub">Entregas Perfectas</span></div><div class="card-icon" style="background:rgba(16,185,129,0.15);">🎯</div></div>
            <div class="card-value text-neon-green">{cumpl_entrega['pct']:.1f}%{render_pill(wow_otif, wow_label)}</div>
            <div class="card-change">{cumpl_entrega['on_time']}/{cumpl_entrega['total']} on time</div>
        </div>
        <div class="card" onclick="showModal('pct_surtido')" data-accent="green">
            <div class="card-header"><div class="card-label">Fill Rate<span class="card-sub">Tasa de Surtido</span></div><div class="card-icon" style="background:rgba(16,185,129,0.15);">📊</div></div>
            <div class="card-value text-neon-green">{pct_surtido['pct']:.1f}%</div>
            <div class="card-change">{pct_surtido.get('surtido', 0):,.0f}/{pct_surtido.get('total', 0):,.0f} piezas</div>
        </div>
        <div class="card" onclick="showModal('audit_quality')" data-accent="cyan">
            <div class="card-header"><div class="card-label">Fulfillment Completion<span class="card-sub">Cumplimiento Surtidos</span></div><div class="card-icon" style="background:rgba(6,182,212,0.15);">📊</div></div>
            <div class="card-value text-neon-cyan">{audit_quality['pct']:.1f}%{render_pill(wow_fulfillment, wow_label)}</div>
            <div class="card-change">{audit_quality['total']} surtidos procesados</div>
        </div>
        <div class="card" onclick="showModal('vol_surtido')" data-accent="purple">
            <div class="card-header"><div class="card-label">Outbound Throughput<span class="card-sub">Volumen de Salida</span></div><div class="card-icon" style="background:rgba(139,92,246,0.15);">📦</div></div>
            <div class="card-value text-neon-purple">{vol_surtido['surtido']:,.0f}</div>
            <div class="card-change">{vol_surtido['ordenes']} orders</div>
        </div>
        <div class="card" onclick="showModal('avance_etapa')" data-accent="blue">
            <div class="card-header"><div class="card-label">Pipeline Velocity<span class="card-sub">Velocidad de Flujo</span></div><div class="card-icon" style="background:rgba(59,130,246,0.15);">📊</div></div>
            <div class="card-value text-neon-blue">{avance_etapa['surtido']:.0f}%</div>
            <div class="card-change">Global Picking Avg</div>
        </div>
        <div class="card" onclick="showModal('wip_metrics')" data-accent="blue">
            <div class="card-header"><div class="card-label">Active Work (WIP)<span class="card-sub">Avance Ordenes Activas</span></div><div class="card-icon" style="background:rgba(59,130,246,0.15);">🚧</div></div>
            <div class="card-value text-neon-blue">{wip_metrics['avance']:.1f}%</div>
            <div class="card-change">{wip_metrics['piezas_pendientes']:,.0f} pzas pendientes</div>
        </div>
        <div class="card" onclick="showModal('backlog')" data-accent="red">
            <div class="card-header"><div class="card-label">Order Backlog<span class="card-sub">Pedidos Pendientes</span></div><div class="card-icon" style="background:rgba(239,68,68,0.15);">📋</div></div>
            <div class="card-value text-neon-red">{backlog['display_backlog']}</div>
            <div class="card-change">{backlog['critical']} Critical / {backlog['total']} Active</div>
        </div>
    </div>
    
    <div class="section-title">📊 Gráficos</div>
    <div class="grid-4">
        <div class="chart-box" onclick="showChartModal('comp')">
            <div class="chart-title">📈 SLA Compliance 72h<span class="chart-sub">Cumplimiento SLA</span></div>
            <div class="chart-wrapper"><canvas id="compChart"></canvas></div>
        </div>
        <div class="chart-box" onclick="showChartModal('vol')">
            <div class="chart-title">📦 Inbound Volume (Weekly)<span class="chart-sub">Volumen de Entrada Semanal</span></div>
            <div class="chart-wrapper"><canvas id="volChart"></canvas></div>
        </div>
        <div class="chart-box" onclick="showChartModal('trend')">
            <div class="chart-title">📉 Outbound Throughput<span class="chart-sub">Surtidos por Semana</span></div>
            <div class="chart-wrapper"><canvas id="trendChart"></canvas></div>
        </div>
        <div class="chart-box" onclick="showChartModal('otd')">
            <div class="chart-title">🎯 OTIF Performance<span class="chart-sub">Desempeño de Entregas</span></div>
            <div class="chart-wrapper"><canvas id="otdChart"></canvas></div>
        </div>
        <div class="chart-box" onclick="showChartModal('tipo')">
            <div class="chart-title">📦 SKU Mix Distribution<span class="chart-sub">Distribución por Tipo</span></div>
            <div class="chart-wrapper"><canvas id="tipoChart"></canvas></div>
        </div>
        <div class="chart-box" onclick="showChartModal('status')">
            <div class="chart-title">🏷️ Order Status Mix<span class="chart-sub">Estatus de Órdenes</span></div>
            <div class="chart-wrapper"><canvas id="statusChart"></canvas></div>
        </div>
        <div class="chart-box" onclick="showChartModal('clientes')">
            <div class="chart-title">👤 Top Clients Volume<span class="chart-sub">Volumen por Cliente</span></div>
            <div class="chart-wrapper"><canvas id="clientChart"></canvas></div>
        </div>
        <div class="chart-box" onclick="showChartModal('pipeline')">
            <div class="chart-title">📊 Fulfillment Pipeline<span class="chart-sub">Embudo de Surtido</span></div>
            <div class="chart-wrapper"><canvas id="pipeChart"></canvas></div>
        </div>
    </div>
</div> <!-- End of main-scroll-area -->

<!-- MODAL -->
<div class="modal-overlay" id="modalOverlay" onclick="closeModal()"></div>
<div class="modal-box" id="modalBox" style="display:none;">
    <div class="modal-header">
        <div class="modal-title" id="modalTitle"></div>
        <button class="close-btn" onclick="closeModal()">×</button>
    </div>
    <div class="modal-body" id="modalBody">
        <div class="chart-container" style="position: relative; height: 180px; width: 100%; margin-bottom: 1rem;">
            <canvas id="modalChartCanvas"></canvas>
        </div>
        <div id="modalContent"></div>
    </div>
    <div class="tech-details" id="modalTech"></div>
    <div class="modal-footer">
        <button class="btn-tech" onclick="toggleTech()" title="Ver detalle técnico">ℹ️</button>
        <button class="btn-close" onclick="closeModal()">Cerrar</button>
    </div>
</div>
</body>
"""

# Assemble Final HTML
# Note: We must not format css_content/js_content with f-string, as they contain {}
html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3PL Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@600&display=swap" rel="stylesheet">
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
        }
        body { background: var(--bg) !important; color: var(--text) !important; }
        .topbar { background: #010409 !important; border-bottom: 1px solid var(--border) !important; justify-content: center !important; }
        .header-text h1 { color: #f0f6fc !important; }
        .signature { 
            font-size: 1.2rem !important; 
            opacity: 1.0 !important; 
            color: #ff3131 !important; 
            text-shadow: 0 0 10px #ff0000 !important;
            bottom: -5px !important;
            right: -100px !important;
        }
        .card, .chart-box { 
            background: var(--card) !important; 
            border: 1px solid var(--border) !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        .card:hover[data-accent="green"] { border-color: #10b981 !important; box-shadow: 0 8px 30px rgba(16, 185, 129, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="red"] { border-color: #ef4444 !important; box-shadow: 0 8px 30px rgba(239, 68, 68, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="orange"] { border-color: #f59e0b !important; box-shadow: 0 8px 30px rgba(245, 158, 11, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="purple"] { border-color: #8b5cf6 !important; box-shadow: 0 8px 30px rgba(139, 92, 246, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="blue"] { border-color: #3b82f6 !important; box-shadow: 0 8px 30px rgba(59, 130, 246, 0.15) !important; transform: translateY(-3px) !important; }
        .card:hover[data-accent="cyan"] { border-color: #06b6d4 !important; box-shadow: 0 8px 30px rgba(6, 182, 212, 0.15) !important; transform: translateY(-3px) !important; }
        .chart-box:hover { border-color: var(--blue) !important; transform: translateY(-3px) !important; }
        .card-label, .card-sub, .chart-sub, .card-change { color: var(--muted) !important; }
        .status-bar.connected { background: #0d1117 !important; color: #3fb950 !important; border-bottom: 1px solid #238636 !important; }
        .notification-trigger { background: #21262d !important; border-color: var(--border) !important; color: #f0f6fc !important; }
        .notification-trigger:hover { background: #30363d !important; }
        .section-title { color: #f0f6fc !important; }
        .section-title::after { background: var(--border) !important; }
        .modal-box { background: #161b22 !important; color: #f0f6fc !important; border: 1px solid var(--border) !important; }
        .modal-header { border-bottom-color: var(--border) !important; }
        .close-btn { color: var(--muted) !important; }
        .close-btn:hover { color: #f0f6fc !important; }
        
        /* Inner Modal visibility fixes */
        .info-box { background: rgba(88, 166, 255, 0.05) !important; border-left: 4px solid var(--blue) !important; color: #f0f6fc !important; padding: 12px !important; border-radius: 4px !important; }
        .exec-summary { background: #0d1117 !important; border-left: 4px solid var(--blue) !important; color: #8b949e !important; padding: 12px !important; border-radius: 8px !important; margin-bottom: 12px !important; }
        .exec-header { color: #f0f6fc !important; font-weight: 800 !important; margin-bottom: 8px !important; }
        .exec-body { color: #c9d1d9 !important; }
        .info-list li { color: #8b949e !important; }
        .info-title { color: #f0f6fc !important; margin-top: 15px !important; margin-bottom: 8px !important; }
        
        .tech-details { background: #0d1117 !important; color: #8b949e !important; border: 1px solid var(--border) !important; padding: 15px !important; border-radius: 8px !important; font-family: monospace !important; }
        .tech-tag { background: #21262d !important; color: #58a6ff !important; border: 1px solid rgba(56, 139, 253, 0.4) !important; }

        table th { border-bottom: 2px solid var(--border) !important; color: var(--muted) !important; }
        table td { border-bottom: 1px solid var(--border) !important; color: #c9d1d9 !important; }
        tr:hover td { background: rgba(255,255,255,0.05) !important; }

        .btn-close { background: #21262d !important; color: #c9d1d9 !important; border: 1px solid var(--border) !important; padding: 8px 20px !important; border-radius: 8px !important; }
        .btn-close:hover { background: #30363d !important; color: #f0f6fc !important; }
        .btn-tech { background: transparent !important; color: var(--muted) !important; border: 1px solid var(--border) !important; }
        .btn-tech:hover { border-color: var(--blue) !important; color: var(--blue) !important; }

        .text-green { color: #3fb950 !important; }
        .text-red { color: #f85149 !important; }

        /* NEON GRADIENTS - 2026 */
        .text-neon-green {
            background: linear-gradient(135deg, #4ade80, #10b981) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 0 20px rgba(16, 185, 129, 0.3) !important;
        }
        .text-neon-red {
            background: linear-gradient(135deg, #f87171, #ef4444) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 0 20px rgba(239, 68, 68, 0.3) !important;
        }
        .text-neon-orange {
            background: linear-gradient(135deg, #fbbf24, #f59e0b) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 0 20px rgba(245, 158, 11, 0.3) !important;
        }
        .text-neon-purple {
            background: linear-gradient(135deg, #a78bfa, #8b5cf6) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 0 20px rgba(139, 92, 246, 0.3) !important;
        }
        .text-neon-blue {
            background: linear-gradient(135deg, #60a5fa, #3b82f6) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 0 20px rgba(59, 130, 246, 0.3) !important;
        }
        .text-neon-cyan {
            background: linear-gradient(135deg, #22d3ee, #06b6d4) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 0 20px rgba(6, 182, 212, 0.3) !important;
        }
    </style>
</head>
""" + html_body + """
<script>
    /* CHART.JS DARK THEME DEFAULTS */
    if (typeof Chart !== 'undefined') {
        Chart.defaults.color = '#8b949e';
        Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
        Chart.defaults.elements.line.borderWidth = 2;
        Chart.defaults.elements.point.radius = 3;
        Chart.defaults.plugins.tooltip.backgroundColor = '#161b22';
        Chart.defaults.plugins.tooltip.titleColor = '#f0f6fc';
        Chart.defaults.plugins.tooltip.bodyColor = '#8b949e';
        Chart.defaults.plugins.tooltip.borderColor = '#30363d';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        
        // Ensure scales are also light
        Chart.defaults.scales.x = { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#8b949e' } };
        Chart.defaults.scales.y = { grid: { color: 'rgba(255, 255, 255, 0.1)' }, ticks: { color: '#8b949e' } };
    }
""" + js_content + """
</script>
</html>
"""

components.html(html_content, height=1000, scrolling=False)
