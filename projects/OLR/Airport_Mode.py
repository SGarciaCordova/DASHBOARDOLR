import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import json
import pytz

# Configuración Horaria
CDMX_TZ = pytz.timezone('America/Mexico_City')

import src.data_loader as data_loader
import src.kpi_engine as kpi_engine

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
now = datetime.now(CDMX_TZ)

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
        # Localizamos a CDMX para evitar el error de naive vs aware
        df_active['fecha_promesa'] = pd.to_datetime(df_active['dt_promesa']).dt.tz_localize(None).dt.tz_localize(CDMX_TZ, ambiguous='infer')
    else:
        # Fallback (should not happen if kpi_engine is updated)
        df_active['fecha_promesa'] = pd.Series(pd.NaT, index=df_active.index).dt.tz_localize(CDMX_TZ)
        
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
    
    orden_cols = ['REFERENCIA WMS', 'REFERENCIA', 'PEDIMENTO', 'NO. PEDIDO', 'ORDEN', 'ID']
    cliente_cols = ['CLIENTE', 'NOMBRE CLIENTE', 'CUSTOMER']
    tipo_cols = ['TIPO DE MERCANCIA', 'TIPO', 'CATEGORIA', 'PRODUCTO']
    
    # Prepare Active JSON
    for _, row in df_active.head(25).iterrows(): # Slightly more items
        cliente = get_col(row, cliente_cols, 'Sin Cliente')[:32]
        orden = get_col(row, orden_cols, 'N/A')[:22]
        tipo = get_col(row, tipo_cols, '-')[:25]
        
        fecha_prom = row.get('fecha_promesa')
        if pd.notna(fecha_prom):
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
            'pendiente': int(row.get('total_pzas', 0)) - int(row.get('surtido_pzas', 0)),
            'status_original': get_col(row, ['STATUS DE SURTIDO'], 'N/A')
        })

    # Prepare Completed JSON
    for _, row in df_completed.iterrows():
        cliente = get_col(row, cliente_cols, 'Sin Cliente')
        orden = get_col(row, orden_cols, 'N/A')
        pzas = row.get('total_pzas', 0)
        surtido = row.get('surtido_pzas', 0)
        tipo = get_col(row, tipo_cols, '-')
        
        fin = row.get('fecha_fin')
        fin_str = fin.strftime('%d/%m %H:%M') if pd.notna(fin) else 'Sin Fecha'
        
        completed_json.append({
            'cliente': cliente,
            'orden': orden,
            'pzas': int(pzas),
            'surtido': int(surtido),
            'tipo': tipo,
            'hora': fin_str,
            'status_text': 'ENTREGADO',
            'status_color': '#3fb950',
            'status_original': get_col(row, ['STATUS DE SURTIDO'], 'N/A')
        })
    
    total_active = len(df_active)
    delayed_count = len(df_active[df_active['status_code'] == 'delayed'])
    risk_count = len(df_active[df_active['status_code'] == 'risk'])
    ontime_count = len(df_active[df_active['status_code'] == 'on_time'])
    ready_count = len(df_active[df_active['status_code'] == 'ready'])
    
    # Store counts for JS
    stats_data = {
        'delayed': {'count': delayed_count, 'label': 'Demorados', 'color': '#ef4444', 'desc': 'Órdenes que ya superaron su fecha promesa de entrega.'},
        'risk': {'count': risk_count, 'label': 'Riesgo Entrega', 'color': '#f59e0b', 'desc': 'Órdenes con menos de 24h restantes y poco avance.'},
        'on_time': {'count': ontime_count, 'label': 'A Tiempo', 'color': '#3b82f6', 'desc': 'Órdenes que se encuentran dentro del cronograma esperado.'},
        'ready': {'count': ready_count, 'label': 'Listas', 'color': '#10b981', 'desc': 'Órdenes con surtido completo, pendientes de embarque.'},
        'total': {'count': total_active, 'label': 'Activas', 'color': '#d2a8ff', 'desc': 'Total de órdenes que se están procesando actualmente.'}
    }
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
            --bg: #0e1117; --card: #161b22;
            --blue: #58a6ff; --green: #3fb950; --orange: #f59e0b; --red: #ef4444; --purple: #d2a8ff; --cyan: #39c5bb;
            --text: #f0f6fc; --muted: #8b949e; --border: #30363d;
        }}
        body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }}
        
        .container-fluid {{ max-width: 100%; padding: 1.5rem 2rem; display: grid; grid-template-columns: 1fr 340px; gap: 2rem; height: 100vh; }}
        
        /* LEFT COLUMN: ACTIVE ORDERS */
        .main-col {{ display: flex; flex-direction: column; overflow: hidden; }}
        
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding: 1rem 1.5rem; background: var(--card); border-radius: 12px; border: 1px solid var(--border); box-shadow: 0 4px 12px rgba(0,0,0,0.3); flex-shrink: 0; }}
        .header-title {{ font-size: 1.8rem; font-weight: 800; color: var(--text); display: flex; align-items: center; gap: 0.75rem; }}
        .header-time {{ text-align: right; }}
        .header-clock {{ font-size: 2.5rem; font-weight: 800; color: var(--text); line-height: 1; }}
        .header-date {{ font-size: 0.9rem; color: var(--muted); }}
        
        .stats {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-bottom: 1.5rem; flex-shrink: 0; }}
        .stat-card {{ background: var(--card); border-radius: 10px; padding: 1rem; text-align: center; border: 1px solid var(--border); border-left: 4px solid; box-shadow: 0 4px 6px rgba(0,0,0,0.2); cursor: pointer; transition: all 0.2s; }}
        .stat-card:hover {{ transform: scale(1.03); border-color: inherit; box-shadow: 0 8px 16px rgba(0,0,0,0.4); }}
        .stat-card.active {{ background: rgba(255,255,255,0.05); border-color: var(--blue) !important; transform: scale(1.05); box-shadow: 0 8px 20px rgba(0,0,0,0.5); }}
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
        
        .order-card {{ background: var(--card); border-radius: 10px; padding: 1.25rem; border: 1px solid var(--border); border-left: 4px solid var(--blue); position: relative; transition: all 0.2s; cursor: pointer; }}
        .order-card:hover {{ transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.4); border-color: var(--blue); }}
        .order-card.delayed {{ border-left-color: var(--red); animation: pulse 2s infinite; }}
        .order-card.risk {{ border-left-color: var(--orange); }}
        .order-card.ready {{ border-left-color: var(--green); background: rgba(63, 185, 80, 0.05); }}
        
        @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.85}} }}
        
        /* RIGHT COLUMN: COMPLETED ORDERS */
        .side-col {{ 
            background: #0d1117; 
            border: 1px solid var(--border); 
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
            border: 1px solid var(--border);
            border-left: 3px solid var(--green);
            opacity: 0.85;
            transition: all 0.2s;
            cursor: pointer;
        }}
        .comp-card:hover {{ opacity: 1; transform: translateX(-4px); border-color: var(--green); box-shadow: -4px 0 12px rgba(63, 185, 80, 0.2); }}
        .comp-header {{ display: flex; justify-content: space-between; align-items: start; }}
        .comp-client {{ font-weight: 700; font-size: 0.9rem; color: #f0f6fc; }}
        .comp-time {{ font-size: 0.75rem; font-weight: 600; color: #3fb950; background: rgba(63, 185, 80, 0.1); padding: 2px 6px; border-radius: 4px; }}
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
        ::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 3px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #8b949e; }}
        
        /* Modal & Footer same as before */
        .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 1000; backdrop-filter: blur(4px); }}
        .modal-overlay.active {{ display: flex; align-items: center; justify-content: center; }}
        .modal-box {{ background: var(--card); border-radius: 16px; padding: 2rem; width: 90%; max-width: 500px; border: 1px solid var(--border); box-shadow: 0 20px 40px rgba(0,0,0,0.6); animation: zoomIn 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275); position: relative; overflow: hidden; }}
        .modal-box::before {{ content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: var(--blue); }}
        .modal-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border); }}
        .modal-title {{ font-size: 1.4rem; font-weight: 800; color: #f0f6fc; }}
        .close-btn {{ background: none; border: none; font-size: 2rem; cursor: pointer; color: var(--muted); line-height: 1; transition: color 0.2s; }}
        .close-btn:hover {{ color: var(--red); }}
        .modal-row {{ display: flex; justify-content: space-between; padding: 0.8rem 0; border-bottom: 1px solid #30363d; }}
        .modal-row:last-of-type {{ border-bottom: none; }}
        .modal-label {{ color: var(--muted); font-size: 0.85rem; font-weight: 500; }}
        .modal-value {{ font-weight: 700; font-size: 0.95rem; color: #f0f6fc; }}
        .modal-footer {{ margin-top: 1.5rem; text-align: right; }}
        .btn-close {{ background: #30363d; color: white; border: none; padding: 0.7rem 2rem; border-radius: 8px; font-weight: 700; cursor: pointer; transition: background 0.2s; }}
        .btn-close:hover {{ background: #444c56; }}
        
        @keyframes zoomIn {{ from {{ transform: scale(0.9); opacity: 0; }} to {{ transform: scale(1); opacity: 1; }} }}
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
                <div class="stat-card" id="stat-delayed" style="border-left-color: var(--red);" onclick="applyFilter('delayed')">
                    <div class="stat-value" style="color: var(--red);">{delayed_count}</div>
                    <div class="stat-label" style="color: var(--red);">⚠️ Demorados</div>
                </div>
                <div class="stat-card" id="stat-risk" style="border-left-color: var(--orange);" onclick="applyFilter('risk')">
                    <div class="stat-value" style="color: var(--orange);">{risk_count}</div>
                    <div class="stat-label" style="color: var(--orange);">⏰ Riesgo</div>
                </div>
                <div class="stat-card" id="stat-on_time" style="border-left-color: var(--blue);" onclick="applyFilter('on_time')">
                    <div class="stat-value" style="color: var(--blue);">{ontime_count}</div>
                    <div class="stat-label" style="color: var(--blue);">✓ A Tiempo</div>
                </div>
                <div class="stat-card" id="stat-ready" style="border-left-color: var(--green);" onclick="applyFilter('ready')">
                    <div class="stat-value" style="color: var(--green);">{ready_count}</div>
                    <div class="stat-label" style="color: var(--green);">🚀 Listas</div>
                </div>
                <div class="stat-card active" id="stat-total" style="border-left-color: var(--purple);" onclick="applyFilter('total')">
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
                Actualizada: {now.strftime('%H:%M:%S')}
            </div>
        </div>
    </div>
    
    <!-- Modal -->
    <div class="modal-overlay" id="modalOverlay" onclick="closeModal()">
        <div class="modal-box" id="modalBox" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-title" id="modalTitle">Detalle de Orden</div>
                <button class="close-btn" onclick="closeModal()">&times;</button>
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
        const stats = {json.dumps(stats_data)};
        let currentFilter = 'total';
        
        function renderOrders() {{
            const filtered = (currentFilter === 'total') ? orders : orders.filter(o => o.status_code === currentFilter);
            const grid = document.getElementById('orderGrid');
            
            if (filtered.length === 0) {{
                grid.innerHTML = `<div style="grid-column: 1/-1; padding: 3rem; text-align: center; color: var(--muted); border: 2px dashed var(--border); border-radius: 12px; font-size: 1.1rem;">Sin órdenes en esta categoría</div>`;
                return;
            }}

            grid.innerHTML = filtered.map((o) => {{
                // Important: we find the original index for showOrderModal
                const originalIndex = orders.findIndex(orig => orig.orden === o.orden);
                
                return `
                <div class="order-card ${{o.status_code}}" onclick="showOrderModal(${{originalIndex}}, 'active')">
                    <div class="order-header">
                        <div>
                            <div class="order-cliente" title="${{o.cliente}}">${{o.cliente}}</div>
                            <div class="order-tipo">📦 ${{o.tipo}}</div>
                        </div>
                        <span class="order-badge" style="background:${{o.status_color}}">${{o.status_text}}</span>
                    </div>
                    <div class="order-grid-details">
                        <div>
                            <div class="order-label">Fecha Compromiso</div>
                            <div class="order-val">${{o.fecha_promesa.split(' ')[0]}}</div>
                            ${{o.fecha_promesa !== '-' ? `<div style="font-size:0.75rem; color:#64748b; margin-top:2px; font-weight:500;">⏰ ${{o.fecha_promesa.split(' ')[1] || ''}}</div>` : ''}}
                        </div>
                        <div style="text-align:right"><div class="order-label">Tiempo Restante</div><div class="order-val" style="color:${{o.status_code==='delayed'?'var(--red)':'inherit'}}">${{o.tiempo}}</div></div>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width:${{o.progress.toFixed(0)}}%; background:${{o.status_color}}"></div>
                    </div>
                    <div class="progress-txt">
                        <span>Pzas: ${{o.surtido.toLocaleString()}} / ${{o.total.toLocaleString()}}</span>
                        <strong>${{o.progress.toFixed(0)}}%</strong>
                    </div>
                </div>`;
            }}).join('');
        }}

        function renderCompleted() {{
            const sideList = document.getElementById('completedList');
            if (completed.length === 0) {{
                sideList.innerHTML = '<div style="color:var(--muted); text-align:center; margin-top:2rem;">Sin salidas recientes</div>';
                return;
            }}
            
            sideList.innerHTML = completed.map((c, i) => `
                <div class="comp-card" onclick="showOrderModal(${{i}}, 'completed')">
                    <div class="comp-header">
                        <div class="comp-client">${{c.cliente}}</div>
                        <div class="comp-time">✅ ${{c.hora}}</div>
                    </div>
                    <div class="comp-order">#${{c.orden}}</div>
                    <div class="comp-pzas">📦 ${{c.pzas.toLocaleString()}} piezas</div>
                </div>
            `).join('');
        }}

        function applyFilter(key) {{
            currentFilter = key;
            
            // Update UI Active State
            document.querySelectorAll('.stat-card').forEach(el => el.classList.remove('active'));
            document.getElementById('stat-' + key).classList.add('active');
            
            renderOrders();
        }}
        
        function showOrderModal(idx, type) {{
            const o = (type === 'active') ? orders[idx] : completed[idx];
            const modalBox = document.getElementById('modalBox');
            modalBox.style.setProperty('--blue', o.status_color || 'var(--green)');
            
            document.getElementById('modalTitle').textContent = type === 'active' ? 'Detalle de Orden Activa' : 'Detalle de Orden Completada';
            
            let content = `
                <div style="margin-bottom: 1.5rem; text-align: center;">
                    <div style="font-size: 1.2rem; font-weight: 700; color: #fff; margin-bottom: 0.25rem;">${{o.cliente}}</div>
                    <div style="font-size: 0.85rem; color: var(--muted);">Orden #${{o.orden}}</div>
                </div>
                
                <div class="modal-row"><span class="modal-label">Tipo de Mercancía</span><span class="modal-value">${{o.tipo}}</span></div>
                <div class="modal-row"><span class="modal-label">${{type === 'active' ? 'Fecha Promesa' : 'Hora de Salida'}}</span><span class="modal-value">${{o.fecha_promesa || o.hora}}</span></div>
                <div class="modal-row"><span class="modal-label">Estatus Dashboard</span><span class="modal-value" style="color:${{o.status_color}}">${{o.status_text}}</span></div>
                <div class="modal-row"><span class="modal-label">Status de Surtido</span><span class="modal-value" style="color:var(--cyan);">${{o.status_original}}</span></div>
            `;

            if (type === 'active') {{
                content += `
                    <div class="modal-row"><span class="modal-label">Avance Surtido</span><span class="modal-value">${{o.progress.toFixed(1)}}%</span></div>
                    <div class="modal-row"><span class="modal-label">Piezas Surtidas</span><span class="modal-value">${{o.surtido.toLocaleString()}}</span></div>
                    <div class="modal-row"><span class="modal-label">Total de Piezas</span><span class="modal-value">${{o.total.toLocaleString()}}</span></div>
                    <div class="modal-row"><span class="modal-label">Pendiente</span><span class="modal-value">${{(o.total - o.surtido).toLocaleString()}} pzas</span></div>
                `;
            }} else {{
                content += `
                    <div class="modal-row"><span class="modal-label">Piezas Totales</span><span class="modal-value">${{o.pzas.toLocaleString()}}</span></div>
                `;
            }}

            document.getElementById('modalContent').innerHTML = content;
            document.getElementById('modalOverlay').classList.add('active');
        }}

        function closeModal() {{
            document.getElementById('modalOverlay').classList.remove('active');
        }}
        
        // Cierra modal con tecla ESC
        window.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});

        renderOrders();
        renderCompleted();
    </script>
</body>
</html>
"""

st.markdown('<style>#MainMenu,footer,.stDeployButton{display:none!important;}.stApp{background:transparent!important;}</style>', unsafe_allow_html=True)

st.components.v1.html(html, height=900, scrolling=True)
