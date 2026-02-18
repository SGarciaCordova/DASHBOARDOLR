import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import json
import os
from datetime import datetime
import subprocess
import time
import sys
import pandas as pd

# st.set_page_config(
#     page_title="Dashboard Reebok",
#     page_icon="👟",
#     layout="wide",
#     initial_sidebar_state="collapsed",
# )

# Hide Streamlit chrome
st.markdown("""
<style>
    #MainMenu, footer, .stDeployButton { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ====== DATABASE CONNECTION & CACHING ======
# Adjust path to find src/ and data/
# Current: projects/Reebok/Dashboard_Reebok.py
# Root is 3 levels up
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "wms_data.db")
ENTRADAS_DIA_EXPR = "SUBSTR(fecha,7,4)||'-'||SUBSTR(fecha,4,2)||'-'||SUBSTR(fecha,1,2)"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@st.cache_data(ttl=300, show_spinner=False)
def load_all_data(db_path_mtime): 
    # db_path_mtime is a dummy argument to force cache invalidation if file changes, 
    # though manual invalidation on refresh is also used.
    conn = get_db_connection()
    
    data = {}
    
    # Check if tables exist
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('entradas', 'surtido')").fetchall()
    existing_tables = [t[0] for t in tables]
    
    if 'entradas' not in existing_tables or 'surtido' not in existing_tables:
        st.error("Error: Tablas no encontradas en la base de datos. Ejecute el scraper para inicializar.")
        return {
            'total_recibos': 0, 'piezas_recibidas': 0, 'skus_unicos': 0, 'tarimas_recibidas': 0, 'tasa_calidad': 0,
            'total_pedidos': 0, 'piezas_surtidas': 0, 'fill_rate': 0, 'tarimas_despachadas': 0, 'pct_completados': 0,
            'last_update': "N/A", 'entradas_data': [], 'surtido_data': [], 'chart_entradas': [], 'chart_surtido': [],
            'chart_skus': [], 'chart_calidad': [], 'chart_tarimas_in': [], 'chart_tarimas_out': [], 'chart_estado': [], 'chart_fillrate': []
        }

    # === KPIs ===
    # INBOUND
    data['total_recibos'] = conn.execute("SELECT COUNT(DISTINCT docto_id) FROM entradas WHERE docto_id IS NOT NULL AND docto_id != ''").fetchone()[0] or 0
    data['piezas_recibidas'] = conn.execute("SELECT COALESCE(SUM(cantidad), 0) FROM entradas").fetchone()[0] or 0
    data['skus_unicos'] = conn.execute("SELECT COUNT(DISTINCT sku) FROM entradas WHERE sku IS NOT NULL AND sku != ''").fetchone()[0] or 0
    data['tarimas_recibidas'] = conn.execute("SELECT COALESCE(SUM(tarimas), 0) FROM entradas").fetchone()[0] or 0
    
    total_con_calidad = conn.execute("SELECT COUNT(*) FROM entradas WHERE calidad IS NOT NULL AND calidad != ''").fetchone()[0] or 1
    calidad_a = conn.execute("SELECT COUNT(*) FROM entradas WHERE UPPER(TRIM(calidad)) = 'A'").fetchone()[0] or 0
    data['tasa_calidad'] = round((calidad_a / total_con_calidad) * 100, 1) if total_con_calidad > 0 else 0

    # OUTBOUND
    data['total_pedidos'] = conn.execute("SELECT COUNT(DISTINCT docto_id) FROM surtido WHERE docto_id IS NOT NULL AND docto_id != ''").fetchone()[0] or 0
    data['piezas_surtidas'] = conn.execute("SELECT COALESCE(SUM(cantidad_surtida), 0) FROM surtido").fetchone()[0] or 0
    
    total_pedida = conn.execute("SELECT COALESCE(SUM(cantidad_pedida), 0) FROM surtido").fetchone()[0] or 0
    total_surtida = conn.execute("SELECT COALESCE(SUM(cantidad_surtida), 0) FROM surtido").fetchone()[0] or 0
    data['fill_rate'] = round((total_surtida / total_pedida * 100), 1) if total_pedida > 0 else 0
    
    data['tarimas_despachadas'] = conn.execute("SELECT COALESCE(SUM(tarimas), 0) FROM surtido").fetchone()[0] or 0
    
    total_con_estado = conn.execute("SELECT COUNT(*) FROM surtido WHERE estado IS NOT NULL AND estado != ''").fetchone()[0] or 1
    completados = conn.execute("SELECT COUNT(*) FROM surtido WHERE UPPER(TRIM(estado)) IN ('SURTIDO', 'COMPLETO', 'COMPLETADO', 'CLOSED', 'CERRADO', 'FINALIZADO')").fetchone()[0] or 0
    data['pct_completados'] = round((completados / total_con_estado) * 100, 1) if total_con_estado > 0 else 0

    data['last_update'] = datetime.fromtimestamp(os.path.getmtime(DB_PATH)).strftime('%d/%m/%Y %H:%M') if os.path.exists(DB_PATH) else datetime.now().strftime('%d/%m/%Y %H:%M')

    # === TABLES ===
    entries = conn.execute("SELECT docto_id, referencia, fecha, sku, descripcion, cantidad, calidad, tarimas FROM entradas ORDER BY rowid DESC LIMIT 50").fetchall()
    data['entradas_data'] = [dict(row) for row in entries]
    
    surtidos = conn.execute("SELECT docto_id, referencia, fecha, hora, cantidad_pedida, cantidad_surtida, tarimas, estado, fill_rate FROM surtido ORDER BY rowid DESC LIMIT 50").fetchall()
    data['surtido_data'] = [dict(row) for row in surtidos]

    # === CHARTS ===
    # Entradas por Dia
    rows = conn.execute(f"SELECT {ENTRADAS_DIA_EXPR} as dia, COUNT(*) as total, COALESCE(SUM(cantidad), 0) as cantidad FROM entradas WHERE fecha IS NOT NULL AND fecha != '' AND LENGTH(fecha) >= 10 GROUP BY dia ORDER BY dia DESC LIMIT 7").fetchall()
    data['chart_entradas'] = [dict(row) for row in reversed(list(rows))]

    # Surtido por Dia
    rows = conn.execute("SELECT DATE(fecha) as dia, COUNT(*) as total, COALESCE(SUM(cantidad_surtida), 0) as cantidad FROM surtido WHERE fecha IS NOT NULL AND fecha != '' GROUP BY DATE(fecha) ORDER BY dia DESC LIMIT 7").fetchall()
    data['chart_surtido'] = [dict(row) for row in reversed(list(rows))]

    # Top SKUs
    rows = conn.execute("SELECT COALESCE(descripcion, sku) as descripcion, SUM(cantidad) as total FROM entradas WHERE sku IS NOT NULL AND sku != '' GROUP BY COALESCE(descripcion, sku) ORDER BY total DESC LIMIT 10").fetchall()
    data['chart_skus'] = [dict(row) for row in rows]

    # Calidad
    rows = conn.execute("SELECT UPPER(TRIM(calidad)) as tipo, COUNT(*) as total FROM entradas WHERE calidad IS NOT NULL AND calidad != '' GROUP BY UPPER(TRIM(calidad)) ORDER BY total DESC").fetchall()
    data['chart_calidad'] = [dict(row) for row in rows]

    # Tarimas In
    rows = conn.execute(f"SELECT {ENTRADAS_DIA_EXPR} as dia, COALESCE(SUM(tarimas), 0) as total FROM entradas WHERE fecha IS NOT NULL AND fecha != '' AND LENGTH(fecha) >= 10 GROUP BY dia ORDER BY dia DESC LIMIT 7").fetchall()
    data['chart_tarimas_in'] = [dict(row) for row in reversed(list(rows))]

    # Tarimas Out
    rows = conn.execute("SELECT DATE(fecha) as dia, COALESCE(SUM(tarimas), 0) as total FROM surtido WHERE fecha IS NOT NULL AND fecha != '' GROUP BY DATE(fecha) ORDER BY dia DESC LIMIT 7").fetchall()
    data['chart_tarimas_out'] = [dict(row) for row in reversed(list(rows))]

    # Estado Pedidos
    rows = conn.execute("SELECT COALESCE(UPPER(TRIM(estado)), 'SIN ESTADO') as estado, COUNT(*) as total FROM surtido GROUP BY COALESCE(UPPER(TRIM(estado)), 'SIN ESTADO') ORDER BY total DESC").fetchall()
    data['chart_estado'] = [dict(row) for row in rows]

    # Fill Rate Dist
    rows = conn.execute("""
        SELECT
            CASE
                WHEN fill_rate >= 100 THEN '100%'
                WHEN fill_rate >= 90 THEN '90-99%'
                WHEN fill_rate >= 70 THEN '70-89%'
                WHEN fill_rate >= 50 THEN '50-69%'
                ELSE '<50%'
            END as rango,
            COUNT(*) as total
        FROM surtido WHERE fill_rate IS NOT NULL
        GROUP BY rango ORDER BY MIN(fill_rate) DESC
    """).fetchall()
    data['chart_fillrate'] = [dict(row) for row in rows]

    conn.close()
    return data



# ====== REFRESH LOGIC ======

col1, col2 = st.columns([1, 6])
with col1:
    if st.button("🔄 Actualizar Datos"):
        status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_status.json")
        
        # Reset status file
        try:
            with open(status_file, "w") as f:
                json.dump({"message": "Iniciando...", "percent": 0, "status": "starting"}, f)
        except:
            pass

        try:
            scraper_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wms_scraper.py")
            process = subprocess.Popen([sys.executable, scraper_script], shell=False)
            
            # Progress Loop 1
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            while True:
                if process.poll() is not None:
                    break
                
                try:
                    if os.path.exists(status_file):
                        with open(status_file, "r") as f:
                            data = json.load(f)
                            pct = data.get("percent", 0)
                            msg = data.get("message", "")
                            status = data.get("status", "")
                            
                            progress_bar.progress(pct)
                            status_text.info(f"Fase 1: {msg} ({pct}%)")
                            
                            if status == "complete" or pct == 100:
                                break
                except:
                    pass
                time.sleep(1)
            
            process.wait()
            
            if process.returncode != 0:
                status_text.error(f"Fase 1 terminó con errores (Código: {process.returncode}). Revisa los logs.")
            else:
                status_text.success("Fase 1 Completada. Iniciando Fase 2...")
                time.sleep(2)
                
                # Reset status file for Phase 2
                try:
                    with open(status_file, "w") as f:
                        json.dump({"message": "Iniciando Finalizados...", "percent": 0, "status": "starting"}, f)
                except:
                    pass

                # Launch Scraper 2: Finalizados
                finalizados_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wms_scraper_embarcados.py")
                process2 = subprocess.Popen([sys.executable, finalizados_script], shell=False)

                while True:
                    if process2.poll() is not None:
                        break
                    
                    try:
                        if os.path.exists(status_file):
                            with open(status_file, "r") as f:
                                data = json.load(f)
                                pct = data.get("percent", 0)
                                msg = data.get("message", "")
                                status = data.get("status", "")
                                
                                progress_bar.progress(pct)
                                status_text.info(f"Fase 2: {msg} ({pct}%)")
                                
                                if status == "complete" or pct == 100:
                                    break
                    except:
                        pass
                    time.sleep(1)
                
                process2.wait()
                
                if process2.returncode == 0:
                    status_text.info("Fase 2 Completada. Unificando datos...")
                    time.sleep(1)
                    
                    # RUN UNIFICADOR
                    try: 
                        unificador_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unificador.py")
                        process_uni = subprocess.Popen([sys.executable, unificador_script], shell=False)
                        process_uni.wait()
                        
                        if process_uni.returncode == 0:
                             status_text.success("¡Actualización Completada (Fase 1, 2 y Unificación)!")
                        else:
                             status_text.error("Error en Unificación.")
                    except Exception as e:
                        status_text.error(f"Error lanzando unificador: {e}")

                    progress_bar.progress(100)
                    time.sleep(2)
                    
                    # CLEAR CACHE ON SUCCESSFUL UPDATE
                    load_all_data.clear()
                    st.rerun()
                else:
                    status_text.error(f"Fase 2 terminó con errores (Código: {process2.returncode}).")

        except Exception as e:
            st.error(f"Error al lanzar el bot: {e}")

# ====== LOAD DATA ======
# We pass last modified time to ensure unique cache key if file changed externally
try:
    db_mtime = os.path.getmtime(DB_PATH)
except:
    db_mtime = 0
    
app_data = load_all_data(db_mtime)

# Display Last Update Prominently
with col2:
    st.markdown(f"**Última Actualización:** {app_data['last_update']}")

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

js_content = js_content.replace('/*REEBOK_KPI_DATA_PLACEHOLDER*/ {}', json.dumps({
    'total_recibos': app_data['total_recibos'],
    'piezas_recibidas': app_data['piezas_recibidas'],
    'skus_unicos': app_data['skus_unicos'],
    'tarimas_recibidas': app_data['tarimas_recibidas'],
    'tasa_calidad': app_data['tasa_calidad'],
    'total_pedidos': app_data['total_pedidos'],
    'piezas_surtidas': app_data['piezas_surtidas'],
    'fill_rate': app_data['fill_rate'],
    'tarimas_despachadas': app_data['tarimas_despachadas'],
    'pct_completados': app_data['pct_completados'],
    'last_update': app_data['last_update']
}))
js_content = js_content.replace('/*REEBOK_ENTRADAS_PLACEHOLDER*/[]', json.dumps(app_data['entradas_data']))
js_content = js_content.replace('/*REEBOK_SURTIDO_PLACEHOLDER*/[]', json.dumps(app_data['surtido_data']))
js_content = js_content.replace('/*REEBOK_CHART_ENTRADAS_PLACEHOLDER*/[]', json.dumps(app_data['chart_entradas']))
js_content = js_content.replace('/*REEBOK_CHART_SURTIDO_PLACEHOLDER*/[]', json.dumps(app_data['chart_surtido']))
js_content = js_content.replace('/*REEBOK_CHART_SKUS_PLACEHOLDER*/[]', json.dumps(app_data['chart_skus']))
js_content = js_content.replace('/*REEBOK_CHART_CALIDAD_PLACEHOLDER*/[]', json.dumps(app_data['chart_calidad']))
js_content = js_content.replace('/*REEBOK_CHART_TARIMAS_IN_PLACEHOLDER*/[]', json.dumps(app_data['chart_tarimas_in']))
js_content = js_content.replace('/*REEBOK_CHART_TARIMAS_OUT_PLACEHOLDER*/[]', json.dumps(app_data['chart_tarimas_out']))
js_content = js_content.replace('/*REEBOK_CHART_ESTADO_PLACEHOLDER*/[]', json.dumps(app_data['chart_estado']))
js_content = js_content.replace('/*REEBOK_CHART_FILLRATE_PLACEHOLDER*/[]', json.dumps(app_data['chart_fillrate']))

# ====== HTML BODY ======
html_body = f"""
<body>

<div class="topbar">
    <div>
        <div class="header-title">⚡ Dashboard Reebok</div>
        <div class="header-sub">Panel de Control Operativo — 10 KPIs</div>
    </div>
    <div>
        <span class="badge badge-time" id="lastUpdate">...</span>
        <span class="badge badge-live">● EN LÍNEA</span>
    </div>
</div>

<div class="container">

    <!-- INBOUND -->
    <div class="section-title inbound">📦 INBOUND — Entradas</div>
    <div class="grid-kpi">
        <div class="card" onclick="openModal('recibos')">
            <div class="card-header">
                <div class="card-label">Total Recibos</div>
                <div class="card-icon" style="background:#dbeafe;color:var(--blue);">📋</div>
            </div>
            <div class="card-value" id="kpi_recibos">—</div>
            <div class="card-footer">Documentos únicos</div>
        </div>
        <div class="card" onclick="openModal('piezas_in')">
            <div class="card-header">
                <div class="card-label">Piezas Recibidas</div>
                <div class="card-icon" style="background:#e0e7ff;color:var(--indigo);">📦</div>
            </div>
            <div class="card-value" id="kpi_piezas_in">—</div>
            <div class="card-footer">Unidades totales</div>
        </div>
        <div class="card" onclick="openModal('skus')">
            <div class="card-header">
                <div class="card-label">SKUs Únicos</div>
                <div class="card-icon" style="background:#f3e8ff;color:var(--purple);">🏷️</div>
            </div>
            <div class="card-value" id="kpi_skus">—</div>
            <div class="card-footer">Productos distintos</div>
        </div>
        <div class="card" onclick="openModal('tarimas_in')">
            <div class="card-header">
                <div class="card-label">Tarimas Recibidas</div>
                <div class="card-icon" style="background:#fce7f3;color:var(--pink);">🎨</div>
            </div>
            <div class="card-value" id="kpi_tarimas_in">—</div>
            <div class="card-footer">Pallets procesados</div>
        </div>
        <div class="card" onclick="openModal('calidad')">
            <div class="card-header">
                <div class="card-label">Tasa Calidad</div>
                <div class="card-icon" style="background:#dcfce7;color:var(--green);">✅</div>
            </div>
            <div class="card-value" id="kpi_calidad">—</div>
            <div class="card-footer">% producto calidad A</div>
        </div>
    </div>

    <!-- OUTBOUND -->
    <div class="section-title outbound">📤 OUTBOUND — Surtido</div>
    <div class="grid-kpi">
        <div class="card" onclick="openModal('pedidos')">
            <div class="card-header">
                <div class="card-label">Total Pedidos</div>
                <div class="card-icon" style="background:#dcfce7;color:var(--green);">📑</div>
            </div>
            <div class="card-value" id="kpi_pedidos">—</div>
            <div class="card-footer">Órdenes procesadas</div>
        </div>
        <div class="card" onclick="openModal('piezas_out')">
            <div class="card-header">
                <div class="card-label">Piezas Surtidas</div>
                <div class="card-icon" style="background:#ccfbf1;color:var(--teal);">📤</div>
            </div>
            <div class="card-value" id="kpi_piezas_out">—</div>
            <div class="card-footer">Unidades despachadas</div>
        </div>
        <div class="card" onclick="openModal('fillrate')">
            <div class="card-header">
                <div class="card-label">Fill Rate</div>
                <div class="card-icon" style="background:#dbeafe;color:var(--blue);">🚀</div>
            </div>
            <div class="card-value" id="kpi_fillrate">—</div>
            <div class="card-footer">Progreso actual</div>
        </div>
        <div class="card" onclick="openModal('tarimas_out')">
            <div class="card-header">
                <div class="card-label">Tarimas Desp.</div>
                <div class="card-icon" style="background:#ffedd5;color:var(--orange);">🚛</div>
            </div>
            <div class="card-value" id="kpi_tarimas_out">—</div>
            <div class="card-footer">Pallets enviados</div>
        </div>
        <div class="card" onclick="openModal('completados')">
            <div class="card-header">
                <div class="card-label">Completados</div>
                <div class="card-icon" style="background:#fef9c3;color:var(--amber);">🏁</div>
            </div>
            <div class="card-value" id="kpi_completados">—</div>
            <div class="card-footer">Pedidos finalizados</div>
        </div>
    </div>

    <!-- INBOUND CHARTS -->
    <div class="section-title inbound">📊 Gráficos Inbound</div>
    <div class="grid-4">
        <div class="chart-box">
            <div class="chart-title">📦 Entradas por Día</div>
            <canvas id="chartEntradasDia" class="chart-canvas"></canvas>
        </div>
        <div class="chart-box">
            <div class="chart-title">🏷️ Top 10 SKUs</div>
            <canvas id="chartSKUs" class="chart-canvas"></canvas>
        </div>
        <div class="chart-box">
            <div class="chart-title">✅ Distribución de Calidad</div>
            <canvas id="chartCalidad" class="chart-canvas"></canvas>
        </div>
        <div class="chart-box">
            <div class="chart-title">🎨 Tarimas Recibidas por Día</div>
            <canvas id="chartTarimasIn" class="chart-canvas"></canvas>
        </div>
    </div>

    <!-- OUTBOUND CHARTS -->
    <div class="section-title outbound">📊 Gráficos Outbound</div>
    <div class="grid-4">
        <div class="chart-box">
            <div class="chart-title">📤 Surtido por Día</div>
            <canvas id="chartSurtidoDia" class="chart-canvas"></canvas>
        </div>
        <div class="chart-box">
            <div class="chart-title">🎯 Distribución Fill Rate</div>
            <canvas id="chartFillRate" class="chart-canvas"></canvas>
        </div>
        <div class="chart-box">
            <div class="chart-title">🏁 Estado de Pedidos</div>
            <canvas id="chartEstado" class="chart-canvas"></canvas>
        </div>
        <div class="chart-box">
            <div class="chart-title">🚛 Tarimas Despachadas por Día</div>
            <canvas id="chartTarimasOut" class="chart-canvas"></canvas>
        </div>
    </div>

</div>

<!-- MODAL -->
<div class="modal-overlay" id="modal" onclick="closeModal()">
    <div class="modal-box" onclick="event.stopPropagation()">
        <div class="modal-header">
            <h2 class="modal-title" id="modal-title">Detalle</h2>
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
    </style>
</head>
""" + html_body + """
<script>
""" + js_content + """
</script>
</html>
"""

components.html(html_content, height=1800, scrolling=True)
