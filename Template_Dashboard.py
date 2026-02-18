import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
import sys

# ==========================================
# 1. CONFIGURACIÓN E IMPORTACIONES
# ==========================================
# Agrega la ruta local para importar tus módulos (data_loader, kpi_engine)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src import data_loader, kpi_engine

st.set_page_config(
    page_title="Nuevo Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. ESTILOS CSS (NO TOCAR PARA MANTENER DISEÑO)
# ==========================================
# Estos estilos replican exactamente la apariencia del Dashboard original
STYLING = """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #f8fafc; --card: #ffffff;
            --blue: #3b82f6; --green: #10b981; --orange: #f59e0b; --red: #ef4444; --purple: #8b5cf6; --cyan: #06b6d4;
            --text: #0f172a; --muted: #64748b; --border: #e2e8f0;
        }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); }
        
        .topbar { background: var(--card); border-bottom: 1px solid var(--border); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
        .header-title { font-size: 2.5rem; font-weight: 800; color: var(--text); letter-spacing: -1px; }
        .header-sub { font-size: 1rem; color: var(--muted); font-weight: 500; }
        
        .container { max-width: 1920px; margin: 0 auto; padding: 2rem; }
        
        /* TARJETAS KPI */
        .grid-kpi { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card { 
            background: var(--card); border-radius: 12px; padding: 1.5rem; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid var(--border);
            transition: all 0.2s; cursor: pointer;
        }
        .card:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.05); border-color: var(--blue); }
        
        .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; }
        .card-label { font-size: 0.85rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }
        .card-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; }
        
        .card-value { font-size: 2rem; font-weight: 800; color: var(--text); margin: 0.5rem 0; }
        .card-footer { font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; gap: 0.5rem; }
        
        /* GRÁFICOS */
        .grid-charts { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; }
        .chart-box { background: var(--card); border-radius: 12px; padding: 1.5rem; border: 1px solid var(--border); height: 350px; }
        .chart-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 1rem; }
        
        /* MODAL */
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; backdrop-filter: blur(2px); }
        .modal-overlay.active { display: flex; align-items: center; justify-content: center; }
        .modal-box { background: var(--card); width: 90%; max-width: 600px; padding: 2rem; border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); animation: pop 0.2s cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes pop { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
        
        .info-row { display: flex; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px solid var(--border); }
        .info-label { color: var(--muted); font-weight: 500; }
        .info-val { font-weight: 700; color: var(--text); }
    </style>
"""

# ==========================================
# 3. CARGA DE DATOS (CONFIGURAR AQUÍ)
# ==========================================
@st.cache_data(ttl=300)
def get_data():
    try:
        # CAMBIAR ESTO: Nombre de tu hoja de cálculo
        SHEET_NAME = "TU_HOJA_DE_GOOGLE_SHEETS"
        
        # Usamos el loader existente
        df_1, df_2, is_mock = data_loader.load_data(SHEET_NAME)
        
        # Si df_2 no existe en tu nuevo caso, ignóralo
        return df_1, is_mock
    except:
        return pd.DataFrame(), True

# Cargar
df, is_mock = get_data()

# ==========================================
# 4. LÓGICA DE NEGOCIO (TUS CÁLCULOS)
# ==========================================
# Ejemplo: Calcular Total Ventas
total_ventas = df['VENTAS'].sum() if 'VENTAS' in df.columns else 0
# Ejemplo: Calcular % Cumplimiento
cumplimiento = 85.5 # Tu lógica aquí

# Preparamos los datos para enviar al Frontend (JavaScript)
kpi_data = {
    'ventas': {'value': total_ventas, 'label': 'Total Ventas', 'desc': 'Ventas acumuladas del mes'},
    'cumplimiento': {'value': cumplimiento, 'label': 'Nivel de Servicio', 'desc': 'Ordenes a tiempo'}
}

# ==========================================
# 5. ESTRUCTURA HTML/JS
# ==========================================
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    {STYLING}
</head>
<body>
    <div class="topbar">
        <div>
            <div class="header-title">Nuevo Dashboard</div>
            <div class="header-sub">Reporte Operativo</div>
        </div>
        <div>
            <!-- Estado Conexión -->
            <span style="background: var({'--cyan' if is_mock else '--green'}); color: white; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.8rem;">
                {'MODO DEMO' if is_mock else 'CONECTADO'}
            </span>
        </div>
    </div>

    <div class="container">
        <!-- SECCIÓN 1: KPIs -->
        <div class="grid-kpi">
            
            <!-- TARJETA 1 -->
            <div class="card" onclick="openModal('ventas')">
                <div class="card-header">
                    <div class="card-label">KPI Principal</div>
                    <div class="card-icon" style="background: #dbeafe; color: var(--blue);">💰</div>
                </div>
                <div class="card-value">${total_ventas:,.0f}</div>
                <div class="card-footer">
                    <span>Ver desglose detallado</span>
                    <span>→</span>
                </div>
            </div>

            <!-- TARJETA 2 -->
            <div class="card" onclick="openModal('cumplimiento')">
                <div class="card-header">
                    <div class="card-label">Cumplimiento</div>
                    <div class="card-icon" style="background: #dcfce7; color: var(--green);">✅</div>
                </div>
                <div class="card-value">{cumplimiento}%</div>
                <div class="card-footer">
                    <span>Meta: 95%</span>
                </div>
            </div>

            <!-- Agrega más tarjetas copiando el bloque div class="card" -->

        </div>

        <!-- SECCIÓN 2: GRÁFICOS -->
        <div class="grid-charts">
            <div class="chart-box">
                <div class="chart-title">Tendencia Mensual</div>
                <canvas id="chart1"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">Distribución por Categoría</div>
                <canvas id="chart2"></canvas>
            </div>
        </div>
    </div>

    <!-- MODAL (Ventana Emergente) -->
    <div class="modal-overlay" id="modal" onclick="closeModal()">
        <div class="modal-box" onclick="event.stopPropagation()">
            <h2 id="modal-title" style="margin-bottom: 1.5rem;">Detalle</h2>
            <div id="modal-content"></div>
            <button onclick="closeModal()" style="margin-top: 1.5rem; width: 100%; padding: 12px; background: var(--text); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">Cerrar</button>
        </div>
    </div>

    <script>
        // DATOS DESDE PYTHON
        const DATA = {json.dumps(kpi_data)};

        // CONFIGURACIÓN DE GRÁFICOS (Chart.js)
        const ctx1 = document.getElementById('chart1');
        new Chart(ctx1, {{
            type: 'line',
            data: {{
                labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May'],
                datasets: [{{
                    label: 'Ventas',
                    data: [12, 19, 3, 5, 2],
                    borderColor: '#3b82f6',
                    tension: 0.4
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});

        const ctx2 = document.getElementById('chart2');
        new Chart(ctx2, {{
            type: 'doughnut',
            data: {{
                labels: ['A', 'B', 'C'],
                datasets: [{{
                    data: [30, 50, 20],
                    backgroundColor: ['#3b82f6', '#10b981', '#f59e0b']
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});

        // LÓGICA DEL MODAL
        function openModal(key) {{
            const item = DATA[key];
            document.getElementById('modal').classList.add('active');
            document.getElementById('modal-title').innerText = item.label;
            document.getElementById('modal-content').innerHTML = `
                <div class="info-row">
                    <span class="info-label">Valor Actual</span>
                    <span class="info-val">${{item.value}}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Descripción</span>
                    <span class="info-val" style="text-align: right; max-width: 60%;">${{item.desc}}</span>
                </div>
            `;
        }}

        function closeModal() {{
            document.getElementById('modal').classList.remove('active');
        }}
    </script>
</body>
</html>
"""

# Renderizar
st.markdown('<style>#MainMenu,footer,header{display:none!important;}.stApp{background:transparent!important; overflow:hidden;}</style>', unsafe_allow_html=True)
st.components.v1.html(html_content, height=900, scrolling=True)
