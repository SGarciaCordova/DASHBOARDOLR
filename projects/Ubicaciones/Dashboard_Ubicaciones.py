import streamlit as st
import streamlit.components.v1 as components
import json
import os
import base64
import numpy as np
import pandas as pd
from src import ubicaciones_loader

# st.set_page_config(
#     page_title="Ubicaciones por Cliente",
#     page_icon="📍",
#     layout="wide",
#     initial_sidebar_state="collapsed",
# )

# Hide Streamlit chrome
st.markdown("""
<style>
    #MainMenu, footer, .stDeployButton { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Logo helper ────────────────────────────────────────────────
def get_base64_logo():
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

logo_b64 = get_base64_logo()

# ═══════════════════════════════════════════════════════════════
#  LOAD DATA
# ═══════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════
#  LOAD DATA & PRE-COMPUTE VIEWS
# ═══════════════════════════════════════════════════════════════
df_clients = ubicaciones_loader.load_clients()
df_locations = ubicaciones_loader.load_locations()
client_list = ubicaciones_loader.get_client_list(df_clients)

# Define the views we want to pre-compute
# (Label, ClientKey_for_loader, IsAggregate)
views_config = [
    ("General", "ALL", True),   # Aggregate
    ("ON", "ON", False),        # Specific
    ("Reebok", "REEBOK", False), # Specific
    ("Piarena", "PIARENA", False) # Specific
]

master_data = {
    "views": {},
    "client_list": client_list
}

# 1. Load ALL inventory first (optimization)
df_all_inventory = ubicaciones_loader.load_all_inventory()

# 2. Compute data for each view
for label, key, is_agg in views_config:
    # Filter or use full dataset
    if is_agg:
        df_view = df_all_inventory.copy()
    else:
        # Filter by _client column added by load_all_inventory
        if not df_all_inventory.empty and "_client" in df_all_inventory.columns:
            df_view = df_all_inventory[df_all_inventory["_client"] == key].copy()
        else:
            df_view = pd.DataFrame() # No data loaded

    has_data = not df_view.empty

    # Compute metrics
    kpis = ubicaciones_loader.compute_kpis(df_view, df_locations)
    # Customize KPI title for view
    kpis["view_label"] = label
    
    occupancy_by_pasillo = ubicaciones_loader.get_occupancy_by_pasillo(df_view, df_locations) if has_data else []
    top_skus = ubicaciones_loader.get_top_skus(df_view) if has_data else []
    dist_by_level = ubicaciones_loader.get_distribution_by_level(df_view, df_locations) if has_data else []
    heatmap_data = ubicaciones_loader.get_heatmap_data(df_view, df_locations) if has_data else {"pasillos": [], "max_position": 0, "cells": []}

    master_data["views"][label] = {
        "kpis": kpis,
        "has_data": has_data,
        "selected_client": label,
        "occupancy_by_pasillo": occupancy_by_pasillo,
        "top_skus": top_skus,
        "distribution_by_level": dist_by_level,
        "heatmap": heatmap_data
    }

# ── Sanitize numpy types ──────────────────────────────────────
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

master_data = sanitize(master_data)

# ═══════════════════════════════════════════════════════════════
#  LOAD EXTERNAL ASSETS
# ═══════════════════════════════════════════════════════════════
try:
    with open("assets/ubicaciones_style.css", "r", encoding="utf-8") as f:
        css_content = f.read()
    with open("assets/ubicaciones_dashboard.js", "r", encoding="utf-8") as f:
        js_content = f.read()
except Exception as e:
    st.error(f"Error loading assets: {e}")
    css_content = ""
    js_content = ""

# Inject master_data into JS
# We use a specific placeholder: /*UBICACIONES_MASTER_DATA_PLACEHOLDER*/
# (Note: You'll need to update the JS file to match this placeholder or use the old one)
# For now, let's keep the old placeholder string but inject the NEW structure
js_content = js_content.replace("/*UBICACIONES_DATA_PLACEHOLDER*/ {}", json.dumps(master_data))

# ═══════════════════════════════════════════════════════════════
#  BUILD HTML
# ═══════════════════════════════════════════════════════════════

# Build client table rows (static for now)
client_rows_html = ""
for c in client_list[:50]:
    badge = '<span class="badge-data yes">✓ Datos</span>' if c["has_data"] else '<span class="badge-data no">Sin datos</span>'
    row_class = "" 
    client_rows_html += f"""<tr class="{row_class}">
        <td>{c['id']}</td>
        <td>{c['name']}</td>
        <td>{badge}</td>
    </tr>"""

# HTML Template Components
# These are now templates that JS will populate/update, but we need initial structure.
# Actually, since we're doing JS rendering, we can just provide the container structure
# and let JS do the initial render of the "General" view.

# We need the Filter Pills to have data-keys
# We will hardcode the known views for this specific requirement (General, ON, Reebok)
filter_pills_html = """
    <div class="filter-pills">
        <div class="pill filter-pill active" data-key="General" title="Vista general">General</div>
        <div class="pill filter-pill" data-key="ON" title="ON">ON</div>
        <div class="pill filter-pill" data-key="Reebok" title="Reebok">Reebok</div>
        <div class="pill filter-pill" data-key="Piarena" title="Piarena">Piarena</div>
    </div>
"""

# HTML Body
html_body = f"""
<body>
<div class="topbar">
    <div class="logo-section">
        <img src="data:image/png;base64,{logo_b64}" class="header-logo">
        <div class="header-text">
            <h1>Dashboard de Ubicaciones</h1>
            <div class="signature">by Sergio Cordova</div>
        </div>
    </div>
    {filter_pills_html}
</div>

<div class="main-scroll-area">
    <!-- Status Bar -->
    <div id="statusBar" class="status-bar connected">
        <!-- JS will populate -->
        <span>Cargando...</span>
    </div>

    <!-- KPI Section -->
    <div id="kpiSection">
        <!-- JS will inject KPI cards here -->
    </div>

    <!-- Charts Section -->
    <div id="chartsSection">
        <div class="section-title" id="chartsTitle">📈 Análisis</div>
        <div class="grid-4">
            <div class="chart-box" onclick="showChartModal('occupancy')">
                <div class="chart-title">📊 Ocupación por Pasillo<span class="chart-sub">% de ubicaciones con inventario</span></div>
                <div class="chart-wrapper"><canvas id="occupancyChart"></canvas></div>
                <div class="occupancy-legend" style="flex-direction:column; gap:4px; margin-top:12px;">
                    <div style="display:flex; justify-content:space-between; width:100%; font-size:0.65rem; color:var(--text-muted); font-weight:600;">
                        <span>0% (Bajo)</span>
                        <span>50% (Medio)</span>
                        <span>100% (Alto)</span>
                    </div>
                    <div style="width:100%; height:8px; border-radius:4px; background:linear-gradient(to right, #10b981 0%, #f59e0b 50%, #ef4444 100%);"></div>
                </div>
            </div>
            <div class="chart-box" onclick="showChartModal('skus')">
                <div class="chart-title">🏷️ Top 10 SKUs<span class="chart-sub">Mayor cantidad en inventario</span></div>
                <div class="chart-wrapper"><canvas id="topSkusChart"></canvas></div>
            </div>
            <div class="chart-box" onclick="showChartModal('levels')">
                <div class="chart-title">📶 Distribución por Nivel<span class="chart-sub">Piezas por nivel de estantería</span></div>
                <div class="chart-wrapper"><canvas id="levelChart"></canvas></div>
            </div>
        </div>

        <div class="section-title">🗺️ Mapa de Almacén</div>
        <div class="heatmap-container">
            <div class="heatmap-title">Heatmap de Ocupación — Pasillos × Posiciones</div>
            <div class="heatmap-grid" id="heatmapGrid"></div>
            <div class="heatmap-legend">
                <span>Densidad:</span>
                <div class="legend-item"><div class="legend-swatch" style="background:rgba(51,65,85,.3)"></div> Vacío</div>
                <div class="legend-item"><div class="legend-swatch" style="background:#1e3a5f"></div> Bajo</div>
                <div class="legend-item"><div class="legend-swatch" style="background:#3b82f6"></div> Medio</div>
                <div class="legend-item"><div class="legend-swatch" style="background:#6366f1"></div> Alto</div>
                <div class="legend-item"><div class="legend-swatch" style="background:#a855f7"></div> Máximo</div>
            </div>
        </div>
    </div>
     
    <!-- Empty State (Hidden by default) -->
    <div id="emptyState" style="display:none;">
        <div class="no-data-container">
            <div class="no-data-icon">📭</div>
            <div class="no-data-text">No hay datos de inventario para esta vista</div>
            <div class="no-data-sub">Los datos se agregarán cuando se descarguen del WMS</div>
        </div>
    </div>

    <!-- Client Table Section -->
    <div class="section-title">👥 Directorio de Clientes</div>
    <div class="client-table-section">
        <input type="text" id="clientSearch" class="search-box" placeholder="🔍 Buscar cliente...">
        <table class="client-table">
            <thead><tr><th>ID</th><th>Cliente</th><th>Estado</th></tr></thead>
            <tbody id="clientTableBody">
                {client_rows_html}
            </tbody>
        </table>
    </div>
</div>

<!-- TOOLTIP -->
<div class="tooltip" id="tooltip"></div>

<!-- MODAL -->
<div class="modal-overlay" id="modalOverlay" onclick="closeModal()"></div>
<div class="modal-box" id="modalBox" style="display:none;">
    <div class="modal-header">
        <div class="modal-title" id="modalTitle"></div>
        <button class="close-btn" onclick="closeModal()">×</button>
    </div>
    <div class="modal-body" id="modalBody">
        <div class="chart-container" style="position:relative;height:200px;width:100%;margin-bottom:1rem;">
            <canvas id="modalChartCanvas"></canvas>
        </div>
        <div id="modalContent"></div>
    </div>
    <div class="modal-footer">
        <button class="btn-close" onclick="closeModal()">Cerrar</button>
    </div>
</div>
</body>
"""

# Assemble final HTML
html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Ubicaciones</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@600&display=swap" rel="stylesheet">
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

components.html(html_content, height=900, scrolling=False)
