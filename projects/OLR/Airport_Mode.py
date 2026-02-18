import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import json

# Adjust path to find src/
# Current: projects/OLR/Airport_Mode.py
# Root is 3 levels up
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src import data_loader, kpi_engine

# st.set_page_config(
#     page_title="🏗️ Panel de Operaciones",
#     page_icon="🏗️",
#     layout="wide",
#     initial_sidebar_state="collapsed"
# )

# Load data
@st.cache_data(ttl=300)
def load_orders():
    try:
        sheet_name = "REPORTE MR 2026 RICARDO"
        _, df_surtidos, is_mock = data_loader.load_data(sheet_name)
        return df_surtidos, is_mock
    except Exception as e:
        return pd.DataFrame(), True

df_surtidos, is_mock = load_orders()
now = datetime.now()

def get_col(row, candidates, default=''):
    for c in candidates:
        if c in row.index and pd.notna(row[c]) and str(row[c]).strip():
            return str(row[c]).strip()
    return default

# Process data
orders_json = []
completed_json = []

if not df_surtidos.empty:
    df = kpi_engine._derive_status(df_surtidos)
    df['total_pzas'] = kpi_engine.clean_numeric(df, 'TOTAL DE PIEZAS')
    df['surtido_pzas'] = kpi_engine.clean_numeric(df, 'PIEZAS SURTIDAS')
    
    # --- ACTIVE ORDERS ---
    df_active = df[
        (df['Calculated_Status'] != 'ENTREGADO') & 
        (df['total_pzas'] > 0)
    ].copy()
    
    # --- COMPLETED ORDERS (Last 24h or max 10) ---
    # We simulate completion time logic if column doesn't exist, prioritizing 'Ready' or 'Delivered'
    df_completed = df[
        (df['Calculated_Status'].isin(['ENTREGADO', 'LISTO PARA EMBARQUE'])) & 
        (df['total_pzas'] > 0)
    ].copy()
    # In a real scenario, sort by Actual Completion Date. Here we just take head(10) or sort by promise date
    # Attempt to find a completion date col
    comp_date_cols = ['FECHA / HORA ENTREGADO', 'FECHA/HORA ENTREGADO', 'FECHA ENTREGADO', 'FECHA FINAL', 'FECHA A ENTREGAR']
    for col in comp_date_cols:
        if col in df_completed.columns:
            df_completed['fecha_fin'] = pd.to_datetime(df_completed[col], dayfirst=True, errors='coerce')
            break
    else:
        df_completed['fecha_fin'] = pd.NaT # Fallback
        
    # Sort completed: If no date, just take status
    df_completed = df_completed.sort_values('fecha_fin', ascending=False).head(15)

    # Use the robust dt_promesa calculated in kpi_engine (which includes Time)
    if 'dt_promesa' in df_active.columns:
        df_active['fecha_promesa'] = df_active['dt_promesa']
    else:
        # Fallback (should not happen if kpi_engine is updated)
        df_active['fecha_promesa'] = pd.NaT
        
    df_active['progress'] = (df_active['surtido_pzas'] / df_active['total_pzas'] * 100).clip(0, 100)
    df_active['horas_restantes'] = (df_active['fecha_promesa'] - now).dt.total_seconds() / 3600
    
    def get_status(row):
        if row['progress'] >= 99:
            return 'ready', 'LISTO PARA EMBARQUE', '#10b981'
        if pd.notna(row.get('fecha_promesa')) and row['fecha_promesa'] < now:
            return 'delayed', 'DEMORADO', '#ef4444'
        hrs = row.get('horas_restantes', 999)
        if pd.notna(hrs) and hrs < 24 and row['progress'] < 70:
            return 'risk', 'RIESGO ENTREGA', '#f59e0b'
        return 'on_time', 'A TIEMPO', '#3b82f6'
    
    statuses = df_active.apply(get_status, axis=1)
    df_active['status_code'] = [s[0] for s in statuses]
    df_active['status_text'] = [s[1] for s in statuses]
    df_active['status_color'] = [s[2] for s in statuses]
    
    order_map = {'delayed': 0, 'risk': 1, 'on_time': 2, 'ready': 3}
    df_active['sort_order'] = df_active['status_code'].map(order_map)
    df_active = df_active.sort_values(['sort_order', 'fecha_promesa'])
    
    orden_cols = ['REFERENCIA', 'PEDIMENTO', 'NO. PEDIDO', 'ORDEN', 'ID']
    cliente_cols = ['CLIENTE', 'NOMBRE CLIENTE', 'CUSTOMER']
    tipo_cols = ['TIPO DE MERCANCIA', 'TIPO', 'CATEGORIA', 'PRODUCTO']
    
    # Prepare Active JSON
    for _, row in df_active.head(15).iterrows(): # Limit 15 to fit
        cliente = get_col(row, cliente_cols, 'Sin Cliente')[:28]
        orden = get_col(row, orden_cols, 'N/A')[:18]
        tipo = get_col(row, tipo_cols, '-')[:20]
        
        fecha_prom = row.get('fecha_promesa')
        # Format: DD/MM HH:MM (highlight time)
        if pd.notna(fecha_prom):
            # If time is 23:59:59 (default), show only date? 
            # User specifically asked for time from col S.
            # If it has specific time (not 23:59:59), show it clearly.
            if fecha_prom.hour == 23 and fecha_prom.minute == 59 and fecha_prom.second == 59:
                prom_str = fecha_prom.strftime('%d/%m') + " Fin día"
            else:
                prom_str = fecha_prom.strftime('%d/%m %H:%M')
        else:
            prom_str = '-'
        
        horas = row.get('horas_restantes', 0)
        if pd.notna(horas) and horas > 0:
            tiempo_str = f"{int(horas//24)}d {int(horas%24)}h" if horas > 24 else f"{int(horas)}h restantes"
        elif pd.notna(horas) and horas < 0:
            tiempo_str = f"{int(abs(horas))}h retraso"
        else:
            tiempo_str = "-"
        
        if row.get('status_code') == 'ready':
            # Ready orders are still part of the main list, just status 'ready'
            pass 
        
        status_code = row.get('status_code', 'on_time')
        # Ensure distinct color for Ready if needed, but here we just rely on status_color from Python logic
        # user wants "Activas" in another color (Purple for total card).
        # We can keep card colors as is (Green for Ready, Blue for On Time).
        
        orders_json.append({
            'cliente': cliente,
            'orden': orden,
            'tipo': tipo,
            'fecha_promesa': prom_str,
            'tiempo': tiempo_str,
            'progress': float(row.get('progress', 0)),
            'total': int(row.get('total_pzas', 0)),
            'surtido': int(row.get('surtido_pzas', 0)),
            'status_text': row.get('status_text', 'N/A'),
            'status_color': row.get('status_color', '#64748b'),
            'status_code': row.get('status_code', 'on_time'),
            'pendiente': int(row.get('total_pzas', 0)) - int(row.get('surtido_pzas', 0))
        })

    # Prepare Completed JSON
    for _, row in df_completed.iterrows():
        cliente = get_col(row, cliente_cols, 'Sin Cliente')
        orden = get_col(row, orden_cols, 'N/A')
        pzas = row.get('total_pzas', 0)
        # Try to get a time, else use 'Hoy'
        fin = row.get('fecha_fin')
        fin_str = fin.strftime('%d/%m %H:%M') if pd.notna(fin) else 'Sin Fecha'
        
        completed_json.append({
            'cliente': cliente,
            'orden': orden,
            'pzas': int(pzas),
            'hora': fin_str
        })
    
    total_active = len(df_active)
    delayed_count = len(df_active[df_active['status_code'] == 'delayed'])
    risk_count = len(df_active[df_active['status_code'] == 'risk'])
    ontime_count = len(df_active[df_active['status_code'] == 'on_time'])
    ready_count = len(df_active[df_active['status_code'] == 'ready'])
else:
    total_active = delayed_count = risk_count = ontime_count = ready_count = 0

# HTML with Split Layout
html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="1800">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg: #f8fafc; --card: #ffffff;
            --blue: #3b82f6; --green: #10b981; --orange: #f59e0b; --red: #ef4444; --purple: #8b5cf6; --cyan: #06b6d4;
            --text: #0f172a; --muted: #64748b; --border: #e2e8f0;
        }}
        body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }}
        
        .container-fluid {{ max-width: 100%; padding: 1.5rem 2rem; display: grid; grid-template-columns: 1fr 340px; gap: 2rem; height: 100vh; }}
        
        /* LEFT COLUMN: ACTIVE ORDERS */
        .main-col {{ display: flex; flex-direction: column; overflow: hidden; }}
        
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding: 1rem 1.5rem; background: var(--card); border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); flex-shrink: 0; }}
        .header-title {{ font-size: 1.8rem; font-weight: 800; color: var(--text); display: flex; align-items: center; gap: 0.75rem; }}
        .header-time {{ text-align: right; }}
        .header-clock {{ font-size: 2.5rem; font-weight: 800; color: var(--text); line-height: 1; }}
        .header-date {{ font-size: 0.9rem; color: var(--muted); }}
        
        .stats {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-bottom: 1.5rem; flex-shrink: 0; }}
        .stat-card {{ background: var(--card); border-radius: 10px; padding: 1rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid; }}
        .stat-value {{ font-size: 2.2rem; font-weight: 800; }}
        .stat-label {{ font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
        
        .order-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); 
            gap: 1rem; 
            overflow-y: auto; 
            padding-bottom: 2rem; 
            padding-right: 0.5rem;
            align-content: start;
        }}
        
        .order-card {{ background: var(--card); border-radius: 10px; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); cursor: pointer; transition: all 0.2s; border: 2px solid transparent; border-left: 4px solid var(--blue); position: relative; }}
        .order-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); border-color: var(--blue); }}
        .order-card.delayed {{ border-left-color: var(--red); animation: pulse 2s infinite; }}
        .order-card.risk {{ border-left-color: var(--orange); }}
        .order-card.ready {{ border-left-color: var(--green); background: #f0fdf4; }}
        
        @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.85}} }}
        
        /* RIGHT COLUMN: COMPLETED ORDERS */
        .side-col {{ 
            background: #f1f5f9; 
            border-left: 1px solid var(--border); 
            padding: 1.5rem; 
            border-radius: 12px; 
            display: flex; 
            flex-direction: column;
            height: calc(100vh - 3rem);
            overflow: hidden;
        }}
        .side-title {{ font-size: 1.1rem; font-weight: 800; color: var(--muted); margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 1px; display: flex; align-items: center; gap: 0.5rem; }}
        .completed-list {{ overflow-y: auto; flex: 1; padding-right: 0.5rem; }}
        
        .comp-card {{ 
            background: var(--card); 
            border-radius: 8px; 
            padding: 0.8rem; 
            margin-bottom: 0.75rem; 
            border-left: 3px solid var(--green);
            opacity: 0.85;
            transition: all 0.2s;
        }}
        .comp-card:hover {{ opacity: 1; transform: translateX(-2px); }}
        .comp-header {{ display: flex; justify-content: space-between; align-items: start; }}
        .comp-client {{ font-weight: 700; font-size: 0.9rem; color: var(--text); }}
        .comp-time {{ font-size: 0.75rem; font-weight: 600; color: var(--green); background: #dcfce7; padding: 2px 6px; border-radius: 4px; }}
        .comp-order {{ font-size: 0.75rem; color: var(--muted); margin-top: 2px; }}
        .comp-pzas {{ font-size: 0.75rem; color: var(--text); margin-top: 4px; font-weight: 500; }}
        
        /* CARD INTERNALS */
        .order-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.6rem; }}
        .order-cliente {{ font-size: 1.1rem; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 220px; }}
        .order-tipo {{ font-size: 0.8rem; color: var(--cyan); font-weight: 500; margin-top: 2px; }}
        .order-id {{ font-size: 0.7rem; color: var(--muted); margin-top: 2px; }}
        .order-badge {{ padding: 0.25rem 0.6rem; border-radius: 20px; font-size: 0.65rem; font-weight: 700; color: white; }}
        
        .order-grid-details {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-top: 0.6rem; }}
        .order-label {{ font-size: 0.6rem; color: var(--muted); text-transform: uppercase; font-weight: 600; }}
        .order-val {{ font-size: 0.85rem; font-weight: 600; color: var(--text);}}
        
        .progress-bar {{ height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; margin-top: 0.75rem; }}
        .progress-fill {{ height: 100%; border-radius: 3px; }}
        .progress-txt {{ font-size: 0.7rem; color: var(--muted); margin-top: 0.2rem; display: flex; justify-content: space-between; }}

         /* SCROLLBARS */
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 3px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #94a3b8; }}
        
        /* Modal & Footer same as before */
        .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 1000; }}
        .modal-overlay.active {{ display: flex; align-items: center; justify-content: center; }}
        .modal-box {{ background: var(--card); border-radius: 16px; padding: 2rem; width: 90%; max-width: 500px; box-shadow: 0 20px 40px rgba(0,0,0,0.2); animation: slideUp 0.2s; }}
        .modal-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border); }}
        .modal-title {{ font-size: 1.25rem; font-weight: 700; }}
        .close-btn {{ background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--muted); }}
        .modal-row {{ display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid #f1f5f9; }}
        .modal-label {{ color: var(--muted); font-size: 0.85rem; }}
        .modal-value {{ font-weight: 600; font-size: 0.9rem; }}
        .modal-footer {{ margin-top: 1.5rem; text-align: right; }}
        .btn-close {{ background: var(--blue); color: white; border: none; padding: 0.6rem 1.5rem; border-radius: 8px; font-weight: 600; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <!-- LEFT COLUMN: ACTIVE -->
        <div class="main-col">
            <div class="header">
                <div class="header-title"><span style="font-size:2rem;">🏗️</span> Panel de Operaciones</div>
                <div class="header-time">
                    <div class="header-clock">{now.strftime('%H:%M')}</div>
                    <div class="header-date">{now.strftime('%A %d %b').capitalize()}</div>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat-card" style="border-left-color: var(--red);">
                    <div class="stat-value" style="color: var(--red);">{delayed_count}</div>
                    <div class="stat-label" style="color: var(--red);">⚠️ Demorados (Entrega)</div>
                </div>
                <div class="stat-card" style="border-left-color: var(--orange);">
                    <div class="stat-value" style="color: var(--orange);">{risk_count}</div>
                    <div class="stat-label" style="color: var(--orange);">⏰ Riesgo Entrega</div>
                </div>
                <div class="stat-card" style="border-left-color: var(--blue);">
                    <div class="stat-value" style="color: var(--blue);">{ontime_count}</div>
                    <div class="stat-label" style="color: var(--blue);">✓ A Tiempo</div>
                </div>
                <div class="stat-card" style="border-left-color: var(--green);">
                    <div class="stat-value" style="color: var(--green);">{ready_count}</div>
                    <div class="stat-label" style="color: var(--green);">🚀 Listas (Embarque)</div>
                </div>
                <div class="stat-card" style="border-left-color: var(--purple);">
                    <div class="stat-value" style="color: var(--purple);">{total_active}</div>
                    <div class="stat-label" style="color: var(--purple);">📋 Activas</div>
                </div>
            </div>
            
            <div class="order-grid" id="orderGrid"></div>
        </div>
        
        <!-- RIGHT COLUMN: COMPLETED -->
        <div class="side-col">
            <div class="side-title">✅ Salidas Recientes</div>
            <div class="completed-list" id="completedList"></div>
            <div style="margin-top: auto; padding-top: 1rem; text-align: center; font-size: 0.7rem; color: var(--muted);">
                Actualizado: {now.strftime('%H:%M:%S')}
            </div>
        </div>
    </div>
    
    <!-- Modal -->
    <div class="modal-overlay" id="modalOverlay" onclick="closeModal()">
        <div class="modal-box" onclick="event.stopPropagation()">
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
        const orders = {json.dumps(orders_json)};
        const completed = {json.dumps(completed_json)};
        
        function getProgressColor(p) {{
            if (p < 40) return 'var(--red)';
            if (p < 80) return 'var(--orange)';
            return 'var(--green)';
        }}
        
        function renderAll() {{
            // Render Active
            document.getElementById('orderGrid').innerHTML = orders.map((o, i) => `
                <div class="order-card ${{o.status_code}}" onclick="showModal(${{i}})">
                    <div class="order-header">
                        <div>
                            <div class="order-cliente">${{o.cliente}}</div>
                            <div class="order-tipo">📦 ${{o.tipo}}</div>

                        </div>
                        <span class="order-badge" style="background:${{o.status_color}}">${{o.status_text}}</span>
                    </div>
                    <div class="order-grid-details">
                        <div>
                            <div class="order-label">Fecha de Entrega</div>
                            <div class="order-val">${{o.fecha_promesa.split(' ')[0]}}</div>
                            ${{o.fecha_promesa !== '-' ? `<div style="font-size:0.75rem; color:#64748b; margin-top:2px; font-weight:500;">⏰ ${{o.fecha_promesa.split(' ')[1] || ''}}</div>` : ''}}
                        </div>
                        <div style="text-align:right"><div class="order-label">Tiempo</div><div class="order-val" style="color:${{o.status_code==='delayed'?'var(--red)':'inherit'}}">${{o.tiempo}}</div></div>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width:${{o.progress.toFixed(0)}}%; background:${{o.status_color}}"></div>
                    </div>
                    <div class="progress-txt">
                        <span>${{o.surtido.toLocaleString()}} / ${{o.total.toLocaleString()}}</span>
                        <strong>${{o.progress.toFixed(0)}}%</strong>
                    </div>
                </div>
            `).join('');
            
            // Render Completed
            document.getElementById('completedList').innerHTML = completed.map(c => `
                <div class="comp-card">
                    <div class="comp-header">
                        <div class="comp-client">${{c.cliente}}</div>
                        <div class="comp-time">✅ ${{c.hora}}</div>
                    </div>
                    <div class="comp-order">#${{c.orden}}</div>
                    <div class="comp-pzas">📦 ${{c.pzas.toLocaleString()}} piezas</div>
                </div>
            `).join('');
            
            if (completed.length === 0) {{
                document.getElementById('completedList').innerHTML = '<div style="color:var(--muted); text-align:center; margin-top:2rem;">Sin salidas recientes</div>';
            }}
        }}
        
        function showModal(idx) {{
            const o = orders[idx];
            document.getElementById('modalTitle').textContent = o.cliente;
            document.getElementById('modalContent').innerHTML = `
                <div class="modal-row"><span class="modal-label">Orden</span><span class="modal-value">#${{o.orden}}</span></div>
                <div class="modal-row"><span class="modal-label">Tipo</span><span class="modal-value">${{o.tipo}}</span></div>
                <div class="modal-row"><span class="modal-label">Fecha Promesa</span><span class="modal-value">${{o.fecha_promesa}}</span></div>
                <div class="modal-row"><span class="modal-label">Estatus</span><span class="modal-value" style="color:${{o.status_color}}">${{o.status_text}}</span></div>
                <div class="modal-row"><span class="modal-label">Avance</span><span class="modal-value">${{o.progress.toFixed(1)}}%</span></div>
                <div class="modal-row"><span class="modal-label">Piezas Surtidas</span><span class="modal-value">${{o.surtido.toLocaleString()}}</span></div>
                <div class="modal-row"><span class="modal-label">Total Piezas</span><span class="modal-value">${{o.total.toLocaleString()}}</span></div>
            `;
            document.getElementById('modalOverlay').classList.add('active');
        }}
        
        function closeModal() {{
            document.getElementById('modalOverlay').classList.remove('active');
        }}
        
        renderAll();
    </script>
</body>
</html>
"""

st.markdown('<style>#MainMenu,footer,.stDeployButton{display:none!important;}.stApp{background:transparent!important;}</style>', unsafe_allow_html=True)

st.components.v1.html(html, height=900, scrolling=True)
