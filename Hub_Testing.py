import streamlit as st
import streamlit.components.v1 as components
import src.data_loader as data_loader
import src.kpi_engine as kpi_engine
import src.alert_engine as alert_engine
import json
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import pytz
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import base64

# ── SUPABASE CONNECTION (Reebok) ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
DATABASE_URL = os.getenv("DATABASE_URL")
_engine = create_engine(DATABASE_URL)
CDMX_TZ = pytz.timezone('America/Mexico_City')

def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize(i) for i in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return 0.0 if np.isnan(obj) else float(obj)
    elif isinstance(obj, float) and (obj != obj):
        return 0.0
    return obj

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""

# try:
#     st.set_page_config(page_title="Global Overview", layout="wide", initial_sidebar_state="collapsed")
# except:
#     pass

# Interfaz nativa restaurada

# ── REEBOK DATA (Supabase) ──
@st.cache_data(ttl=300, show_spinner=False)
def fetch_real_rbk_data():
    now = datetime.now(CDMX_TZ)
    today_str = now.strftime('%Y-%m-%d')
    week_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d')
    month_ago = (now - timedelta(days=30)).strftime('%Y-%m-%d')

    # Fill Rate & Volume from surtido table per period
    periods = {}
    for key, since in [('hoy', today_str), ('semana', week_ago), ('mes', month_ago)]:
        try:
            with _engine.connect() as conn:
                df_s = pd.read_sql(text(f"SELECT cantidad_pedida, cantidad_surtida FROM surtido WHERE fecha >= :since"), conn, params={"since": since})
            if not df_s.empty:
                total_req = pd.to_numeric(df_s['cantidad_pedida'], errors='coerce').fillna(0).sum()
                total_pick = pd.to_numeric(df_s['cantidad_surtida'], errors='coerce').fillna(0).sum()
                fill = (total_pick / total_req * 100) if total_req > 0 else 0
                vol = int(total_pick)
            else:
                fill, vol = 0, 0
        except:
            fill, vol = 0, 0
        periods[key] = {"fill": round(float(fill), 1), "vol": vol}

    # Alerts from wms_aeropuerto (always current snapshot)
    demoras, riesgo = 0, 0
    order_alerts = []
    try:
        with _engine.connect() as conn:
            df = pd.read_sql(text("SELECT * FROM wms_aeropuerto"), conn)
    except:
        df = pd.DataFrame()

    for _, order in df.iterrows():
        estado = str(order.get('estado', '')).upper().strip()
        if estado in ['EMBARCADO', 'COMPLETO', 'COMPLETADO', 'FINALIZADO', 'CERRADO', 'CLOSED']:
            continue
        f_ingreso = order.get('fecha', '')
        f_entrega = order.get('fecha_entrega', '')
        h_ingreso = order.get('hora', '00:00:00')
        try:
            dt_i = pd.to_datetime(f"{str(f_ingreso).split(' ')[0]} {str(h_ingreso)}")
            if dt_i.tzinfo is None: dt_i = CDMX_TZ.localize(dt_i)
        except: dt_i = now
        if f_entrega and str(f_entrega).lower() not in ['none', ''] and str(f_entrega).strip():
            try:
                deadline = pd.to_datetime(f_entrega)
                if deadline.tzinfo is None: deadline = CDMX_TZ.localize(deadline)
            except: deadline = dt_i + timedelta(hours=36)
        else: deadline = dt_i + timedelta(hours=36)
        pct = 0
        try:
            qr = float(order.get('cantidad_pedida', 0) or 0)
            qp = float(order.get('cantidad_surtida', 0) or 0)
            pct = (qp / qr * 100) if qr > 0 else 0
        except: pass
        if estado in ['SURTIDO', 'LISTAS PARA EMBARQUE'] or pct >= 99 or estado == 'INGRESADO':
            continue
        try:
            if deadline.tzinfo is None: deadline = CDMX_TZ.localize(deadline)
            hours_left = (deadline - now).total_seconds() / 3600.0
            if hours_left <= 4:
                if hours_left < 0: demoras += 1
                else: riesgo += 1
                order_alerts.append({
                    "client": str(order.get('cliente', 'S/C')),
                    "doc": str(order.get('docto_id', 'N/A')),
                    "ref": str(order.get('referencia', 'N/A')),
                    "qty": "", "status": f"Demora >{int(abs(hours_left))}h" if hours_left < 0 else "Riesgo <4h"
                })
        except: pass

    alerts_count = demoras + riesgo
    alert_list = sorted(order_alerts, key=lambda x: x["status"], reverse=True)[:15]

    result = {}
    for key in ['hoy', 'semana', 'mes']:
        result[key] = {"fill": periods[key]["fill"], "vol": periods[key]["vol"],
                       "alerts_count": alerts_count, "alert_list": alert_list}
    return _sanitize(result)


# ── ON DATA (Google Sheets) ──
@st.cache_data(ttl=300, show_spinner=False)
def fetch_real_on_data():
    from src.kpis.surtidos import _derive_status
    from src.kpis.helpers import clean_numeric, clean_numeric_percent
    sheet_name = "REPORTE MR 2026 RICARDO"
    df_ent, df_sur, is_mock = data_loader.load_data(sheet_name)

    now_naive = datetime.now()
    today = now_naive.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Parse date column
    if not df_sur.empty:
        for c in ['FECHA / HORA ENTREGADO', 'FECHA ENTREGADO', 'FECHA']:
            if c in df_sur.columns:
                df_sur['_dt'] = pd.to_datetime(df_sur[c], dayfirst=True, errors='coerce')
                break
        else:
            df_sur['_dt'] = pd.NaT

    # KPIs per period
    periods = {}
    for key, since in [('hoy', today), ('semana', week_ago), ('mes', month_ago)]:
        if df_sur.empty:
            periods[key] = {"fill": 0, "vol": 0}
            continue
        mask = df_sur['_dt'] >= since
        df_f = df_sur[mask]
        
        # Calculate Fill Rate using '% EN PROCESO COMPLETO'
        fill_series = clean_numeric_percent(df_f, '% EN PROCESO COMPLETO')
        fill = fill_series.mean() * 100 if not fill_series.empty else 0
        
        # Calculate Volume using 'PIEZAS SURTIDAS'
        vol = int(clean_numeric(df_f, 'PIEZAS SURTIDAS').sum())
        
        periods[key] = {"fill": round(float(fill), 1), "vol": vol}

    # Alerts (always current snapshot)
    alert_details = []
    delayed_count = 0
    client_issues = {}
    if not df_sur.empty:
        df_status = _derive_status(df_sur)
        now_cdmx = datetime.now(CDMX_TZ).replace(tzinfo=None)
        delayed_df = df_status[df_status['Calculated_Status'] == 'DEMORADO']
        for _, row in delayed_df.iterrows():
            c = str(row.get('CLIENTE', 'Sin cliente'))
            client_issues.setdefault(c, {"qty": 0, "status": "Demorado"})
            client_issues[c]["qty"] += 1
        en_proceso = df_status[df_status['Calculated_Status'] == 'EN PROCESO'].copy()
        if not en_proceso.empty and 'dt_promesa' in en_proceso.columns:
            for _, row in en_proceso.iterrows():
                promesa = row.get('dt_promesa')
                progress = row.get('progress', 0) or 0
                if pd.notna(promesa):
                    hours_left = (promesa - now_cdmx).total_seconds() / 3600.0
                    if 0 < hours_left <= 24 and progress < 70:
                        c = str(row.get('CLIENTE', 'Sin cliente'))
                        client_issues.setdefault(c, {"qty": 0, "status": "Riesgo"})
                        client_issues[c]["qty"] += 1
        delayed_count = sum(v["qty"] for v in client_issues.values())
        if client_issues:
            alert_details = sorted(
                [{"client": c, "qty": f"{v['qty']} órdenes", "status": v["status"]} for c, v in client_issues.items()],
                key=lambda x: x["qty"], reverse=True
            )[:6]

    result = {}
    for key in ['hoy', 'semana', 'mes']:
        result[key] = {"fill": periods[key]["fill"], "vol": periods[key]["vol"],
                       "alerts_count": delayed_count, "alert_list": alert_details}
    return _sanitize(result)

real_on = fetch_real_on_data()
real_rbk = fetch_real_rbk_data()





hub_html = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Orbitron:wght@500;700;900&family=Great+Vibes&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
/* Scrollbars */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); border-radius: 4px; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.3); }

body {
    font-family: 'Inter', system-ui, sans-serif;
    background: #0e1117;
    background-image:
        radial-gradient(ellipse at 25% 0%, rgba(56,189,248,0.03) 0%, transparent 55%),
        radial-gradient(ellipse at 75% 0%, rgba(244,63,94,0.02) 0%, transparent 55%),
        radial-gradient(ellipse at 50% 100%, rgba(20,20,30,0.4) 0%, transparent 40%);
    color: #f0f6fc;
    min-height: 100vh;
    padding: 10px 20px 20px;
}

.header { 
    display: flex; 
    align-items: center; 
    justify-content: center;
    gap: 30px; 
    margin-bottom: 40px; 
    width: 100%;
}
.logo-container {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 90px;
    height: 90px;
}
.logo-container img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}
.title-container {
    display: flex;
    flex-direction: column;
}
.main-title {
    font-size: 58px;
    font-weight: 800;
    color: #fff;
    line-height: 0.9;
    letter-spacing: -2px;
    margin: 0;
}
.signature {
    font-family: 'Great Vibes', cursive;
    font-size: 26px; /* A bit bigger as requested */
    color: #ff3131; /* Neon Red */
    margin-top: -5px;
    margin-left: 375px; /* Precisely under 'b' of 'Hub' */
    white-space: nowrap;
    text-shadow: 0 0 10px #ff0000, 0 0 20px rgba(255, 0, 0, 0.5); /* Stronger Neon Glow */
}
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; max-width: 1300px; margin: 0 auto; }
.card {
    position: relative; border-radius: 18px; overflow: hidden;
    transition: transform 0.4s cubic-bezier(0.25,0.46,0.45,0.94), box-shadow 0.4s;
    background: #161b22;
}
.card:hover { transform: translateY(-3px); }
.card::before {
    content: ''; position: absolute; inset: 0; border-radius: 18px; padding: 1.5px;
    background: linear-gradient(180deg, #30363d 0%, rgba(48,54,61,0.2) 50%, #30363d 100%);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor; mask-composite: exclude; pointer-events: none; z-index: 2;
}
.card::after {
    content: ''; position: absolute; top: 0; left: 10%; right: 10%; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(88,166,255,0.2), transparent); z-index: 3;
}
.card-bg { position: absolute; inset: 1.5px; border-radius: 17px; z-index: 0; }
.card.reebok .card-bg { background: radial-gradient(circle at 0% 0%, rgba(88,166,255,0.08) 0%, transparent 60%); }
.card.on .card-bg { background: radial-gradient(circle at 0% 0%, rgba(244,63,94,0.08) 0%, transparent 60%); }
.card-content { position: relative; z-index: 1; padding: 24px 28px 0; }
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
.card-label { font-size: 10px; font-weight: 500; letter-spacing: 3px; color: rgba(255,255,255,0.25); text-transform: uppercase; }
.pill { padding: 6px 16px; border-radius: 20px; font-size: 11px; font-weight: 500; letter-spacing: 1.5px; text-transform: uppercase; }
.pill-green { background: rgba(52,211,153,0.1); color: #34d399; border: 1px solid rgba(52,211,153,0.25); }
.pill-amber { background: rgba(251,191,36,0.1); color: #fbbf24; border: 1px solid rgba(251,191,36,0.25); }
.pill-red { background: rgba(248,113,113,0.1); color: #f87171; border: 1px solid rgba(248,113,113,0.25); }
.card-name { font-size: 26px; font-weight: 400; color: #f1f5f9; margin-bottom: 20px; letter-spacing: -0.5px; }
.filters { display: flex; gap: 5px; margin-bottom: 12px; }
.fbtn {
    padding: 5px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.07);
    background: rgba(255,255,255,0.02); color: rgba(255,255,255,0.35);
    font-size: 11px; font-weight: 500; cursor: pointer; transition: all 0.25s; user-select: none;
}
.fbtn:hover { border-color: rgba(255,255,255,0.12); color: rgba(255,255,255,0.55); }
.fbtn.active { background: rgba(255,255,255,0.07); color: #fff; border-color: rgba(255,255,255,0.18); }
.kpi-row { display: flex; align-items: center; gap: 10px; min-height: 220px; }
.nav-btn {
    width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;
    border-radius: 10px; border: 1px solid rgba(255,255,255,0.05); background: rgba(255,255,255,0.02);
    color: rgba(255,255,255,0.18); font-size: 20px; cursor: pointer; transition: all 0.3s; flex-shrink: 0; user-select: none;
}
.nav-btn:hover { border-color: rgba(255,255,255,0.12); color: rgba(255,255,255,0.5); }
.kpi-center { flex: 1; animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
.kpi-title { font-size: 10px; font-weight: 500; letter-spacing: 2px; color: rgba(255,255,255,0.28); text-transform: uppercase; margin-bottom: 4px; }
.kpi-val { font-size: 54px; font-weight: 300; line-height: 1; letter-spacing: -2px; margin-bottom: 4px; }
.kpi-sub { font-size: 12px; font-weight: 400; }
.kpi-val.clickable { cursor: pointer; transition: text-shadow 0.3s; }
.kpi-val.clickable:hover { text-shadow: 0 0 20px currentColor; }
.alert-detail {
    margin-top: 12px; padding: 12px 16px; border-radius: 10px;
    background: rgba(248,113,113,0.06); border: 1px solid rgba(248,113,113,0.12);
    font-size: 12px; color: rgba(255,255,255,0.65); line-height: 1.6; animation: fadeIn 0.3s ease;
    max-height: 160px; overflow-y: auto; overflow-x: hidden; padding-right: 8px;
}
.alert-detail strong { color: #f87171; }
.alert-row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.alert-row:last-child { border-bottom: none; }
.enter-btn {
    display: block; width: 100%; padding: 14px; text-align: center;
    font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.3); letter-spacing: 0.5px;
    border-top: 1px solid rgba(255,255,255,0.05); cursor: pointer; transition: all 0.3s;
    text-decoration: none; position: relative; z-index: 10;
}
.enter-btn:hover { background: rgba(255,255,255,0.03); color: rgba(255,255,255,0.65); }
.card.reebok .enter-btn:hover { color: #38bdf8; }
.card.on .enter-btn:hover { color: #f43f5e; }
.alert-row:last-child { border-bottom: none; }
.c-blue { color: #38bdf8; } .c-green { color: #34d399; } .c-red { color: #f87171; }
.c-pink { color: #f472b6; } .c-amber { color: #fbbf24; } .c-muted { color: rgba(255,255,255,0.25); }
.spark-wrap { margin-top: 14px; height: 75px; }
.spark-wrap svg { width: 100%; height: 100%; display:block; }
.dots { display: flex; gap: 7px; justify-content: center; margin-top: 18px; padding-bottom: 16px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: rgba(255,255,255,0.08); transition: all 0.3s; }
.dot.active { width: 22px; border-radius: 4px; }
.dot.active.blue { background: #38bdf8; box-shadow: 0 0 8px rgba(56,189,248,0.4); }
.dot.active.pink { background: #f43f5e; box-shadow: 0 0 8px rgba(244,63,94,0.4); }
.enter-btn {
    display: block; width: 100%; padding: 14px; text-align: center;
    font-size: 13px; font-weight: 400; color: rgba(255,255,255,0.3); letter-spacing: 0.5px;
    border-top: 1px solid rgba(255,255,255,0.05); cursor: pointer; transition: all 0.3s;
    text-decoration: none; position: relative; z-index: 1;
}
.enter-btn:hover { background: rgba(255,255,255,0.03); color: rgba(255,255,255,0.65); }
.card.reebok .enter-btn:hover { color: #38bdf8; }
.card.on .enter-btn:hover { color: #f43f5e; }
.strip {
    max-width: 1300px; margin: 24px auto 0; display: grid; grid-template-columns: repeat(4, 1fr);
    border-radius: 14px; overflow: hidden; position: relative;
    border: 1px solid var(--border);
}
.strip::before {
    content: ''; position: absolute; inset: 0; border-radius: 14px; padding: 1px;
    background: linear-gradient(180deg, #30363d, transparent, #30363d);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor; mask-composite: exclude; pointer-events: none; z-index: 2;
}
.strip-bg { position: absolute; inset: 0; border-radius: 13px; background: #161b22; z-index: 0; }
.strip-col { position: relative; z-index: 1; text-align: center; padding: 20px 14px; transition: background 0.3s; }
.strip-col + .strip-col { border-left: 1px solid #30363d; }
.strip-col.clickable { cursor: pointer; }
.strip-col.clickable:hover { background: rgba(255,255,255,0.03); }
.strip-label { font-size: 9px; font-weight: 500; letter-spacing: 2px; color: #8b949e; text-transform: uppercase; margin-bottom: 5px; }
.strip-val { font-size: 26px; font-weight: 400; color: #f0f6fc; margin-bottom: 2px; transition: all 0.3s; }
.strip-sub { font-size: 10px; font-weight: 400; }
.sparkle { position: fixed; bottom: 20px; right: 30px; font-size: 28px; color: rgba(255,255,255,0.03); pointer-events: none; animation: pulse 4s infinite; }
@keyframes pulse { 0%,100% { transform: scale(1) rotate(0deg); opacity: 0.03; } 50% { transform: scale(1.1) rotate(10deg); opacity: 0.08; } }
#error-log { position: fixed; top: 0; left: 0; width: 100%; background: #ef4444; color: white; z-index: 9999; padding: 10px; display: none; font-family: monospace; font-size: 14px; }
</style>
</head>
<body>
<div id="error-log"></div>
<script>
window.onerror = function(msg, url, lineNo, columnNo, error) {
    document.getElementById('error-log').style.display = 'block';
    document.getElementById('error-log').innerHTML += "JS ERROR: " + msg + " at line " + lineNo + "<br/>";
    return false;
};
</script>

<div class="header">
    <div class="logo-container">
        <img src="data:image/png;base64,<!--LOGO_B64-->" alt="OLR Logo">
    </div>
    <div class="title-container">
        <h1 class="main-title">Command Hub</h1>
        <div class="signature">by Sergio Cordova</div>
    </div>
</div>

<div class="grid">
    <!-- REEBOK -->
    <div class="card reebok" id="card-rbk">
        <div class="card-bg"></div>
        <div class="card-content">
            <div class="filters" id="filters-rbk">
                <div class="fbtn" onclick="setFilter('rbk','hoy',this)">Hoy</div>
                <div class="fbtn active" onclick="setFilter('rbk','semana',this)">Esta Semana</div>
                <div class="fbtn" onclick="setFilter('rbk','mes',this)">Este Mes</div>
            </div>
            <div class="card-head">
                <span class="card-label">Account</span>
                <span class="pill" id="pill-rbk"></span>
            </div>
            <div class="card-name">Reebok Operation</div>
            <div class="kpi-row">
                <div class="nav-btn" onclick="navCard('rbk',-1)">‹</div>
                <div class="kpi-center" id="kpi-rbk"></div>
                <div class="nav-btn" onclick="navCard('rbk',1)">›</div>
            </div>
            <div class="dots" id="dots-rbk"></div>
        </div>
        <div class="enter-btn" onclick="enterDashboard('reebok')">✈  INGRESAR A DASHBOARD REEBOK</div>
    </div>

    <!-- ON -->
    <div class="card on" id="card-on">
        <div class="card-bg"></div>
        <div class="card-content">
            <div class="filters" id="filters-on">
                <div class="fbtn" onclick="setFilter('on','hoy',this)">Hoy</div>
                <div class="fbtn active" onclick="setFilter('on','semana',this)">Esta Semana</div>
                <div class="fbtn" onclick="setFilter('on','mes',this)">Este Mes</div>
            </div>
            <div class="card-head">
                <span class="card-label">Account</span>
                <span class="pill" id="pill-on"></span>
            </div>
            <div class="card-name">ON Operation</div>
            <div class="kpi-row">
                <div class="nav-btn" onclick="navCard('on',-1)">‹</div>
                <div class="kpi-center" id="kpi-on"></div>
                <div class="nav-btn" onclick="navCard('on',1)">›</div>
            </div>
            <div class="dots" id="dots-on"></div>
        </div>
        <div class="enter-btn" onclick="enterDashboard('on')">✈  INGRESAR A DASHBOARD ON</div>
    </div>
</div>

<div class="strip" id="global-strip">
    <div class="strip-bg"></div>
    <div class="strip-col">
        <div class="strip-label">Fill Rate Promedio</div>
        <div class="strip-val" id="gs-fill">—</div>
        <div class="strip-sub c-green">Combinado Reebok + ON</div>
    </div>
    <div class="strip-col">
        <div class="strip-label">Volumen Total</div>
        <div class="strip-val" id="gs-vol">—</div>
        <div class="strip-sub c-muted">Unidades procesadas</div>
    </div>
    <div class="strip-col clickable" onclick="showGlobalAlerts()">
        <div class="strip-label">Alertas Activas</div>
        <div class="strip-val c-red" id="gs-alerts">—</div>
        <div class="strip-sub c-red">Click para detalles</div>
    </div>
    <div class="strip-col">
        <div class="strip-label">Última Sincronización</div>
        <div class="strip-val" style="font-size:18px;"><!--LAST_SYNC--></div>
        <div class="strip-sub c-green">● En línea</div>
    </div>
</div>

<div id="global-alert-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.8); backdrop-filter:blur(8px); z-index:9999; align-items:center; justify-content:center; padding:40px; animation: fadeIn 0.3s ease;">
    <div style="background:linear-gradient(160deg, rgba(30,36,50,0.95), rgba(18,22,32,0.98)); border:1px solid rgba(248,113,113,0.3); border-radius:18px; padding:30px; width:100%; max-width:900px; max-height:85vh; overflow-y:auto; overflow-x:hidden; box-shadow: 0 0 60px rgba(248,113,113,0.15);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:15px;">
            <span style="font-size:18px; font-weight:800; color:#f87171; letter-spacing:1px;">⚠ DESGLOSE DE ALERTAS ACTIVAS</span>
            <span style="cursor:pointer; color:rgba(255,255,255,0.4); font-size:24px; transition:color 0.2s;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='rgba(255,255,255,0.4)'" onclick="document.getElementById('global-alert-modal').style.display='none'">✕</span>
        </div>
        <div id="global-alert-content" style="display:grid; grid-template-columns:1fr 1px 1fr; gap:0;"></div>
    </div>
</div>

<div class="sparkle">✦</div>

<script>
// ══════ DATA ══════
// DATA INJECTED FROM PYTHON (ON Real Data)
const REAL_ON_KPI = JSON.parse('<!--DATA_ON-->');
const REAL_RBK_KPI = JSON.parse('<!--DATA_RBK-->');

const DATA = {
    rbk: {
        hoy: [
            { tit:"FILL RATE GLOBAL", val: REAL_RBK_KPI.hoy.fill.toFixed(1)+"%", numVal: REAL_RBK_KPI.hoy.fill, sub:"Surtido de hoy", subC:"c-muted", valC:"c-blue", trend:[88,90,91,89,92,93,REAL_RBK_KPI.hoy.fill], lineC:"#38bdf8", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val: REAL_RBK_KPI.hoy.vol.toLocaleString(), numVal: REAL_RBK_KPI.hoy.vol, sub:"Unidades hoy", subC:"c-muted", valC:"c-green", trend:[3000,3200,3100,3500,3800,4000,REAL_RBK_KPI.hoy.vol], lineC:"#34d399", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS — AIRPORT MODE", val: REAL_RBK_KPI.hoy.alerts_count.toString(), numVal: REAL_RBK_KPI.hoy.alerts_count, sub:"⚠ Requieren atención", subC:"c-red", valC:"c-red", trend:[5,4,6,3,5,4,REAL_RBK_KPI.hoy.alerts_count], lineC:"#f87171", type:"alert",
              alerts: REAL_RBK_KPI.hoy.alert_list }
        ],
        semana: [
            { tit:"FILL RATE GLOBAL", val: REAL_RBK_KPI.semana.fill.toFixed(1)+"%", numVal: REAL_RBK_KPI.semana.fill, sub:"Últimos 7 días", subC:"c-muted", valC:"c-blue", trend:[85,87,89,90,91,90,REAL_RBK_KPI.semana.fill], lineC:"#38bdf8", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val: REAL_RBK_KPI.semana.vol.toLocaleString(), numVal: REAL_RBK_KPI.semana.vol, sub:"Unidades esta semana", subC:"c-muted", valC:"c-green", trend:[22000,23500,25000,26000,27000,28000,REAL_RBK_KPI.semana.vol], lineC:"#34d399", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS — AIRPORT MODE", val: REAL_RBK_KPI.semana.alerts_count.toString(), numVal: REAL_RBK_KPI.semana.alerts_count, sub:"⚠ Requieren atención", subC:"c-red", valC:"c-red", trend:[12,10,15,8,14,11,REAL_RBK_KPI.semana.alerts_count], lineC:"#f87171", type:"alert",
              alerts: REAL_RBK_KPI.semana.alert_list }
        ],
        mes: [
            { tit:"FILL RATE GLOBAL", val: REAL_RBK_KPI.mes.fill.toFixed(1)+"%", numVal: REAL_RBK_KPI.mes.fill, sub:"Últimos 30 días", subC:"c-muted", valC:"c-blue", trend:[80,82,85,87,86,88,REAL_RBK_KPI.mes.fill], lineC:"#38bdf8", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val: REAL_RBK_KPI.mes.vol.toLocaleString(), numVal: REAL_RBK_KPI.mes.vol, sub:"Unidades este mes", subC:"c-muted", valC:"c-green", trend:[90000,95000,100000,105000,108000,110000,REAL_RBK_KPI.mes.vol], lineC:"#34d399", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS — AIRPORT MODE", val: REAL_RBK_KPI.mes.alerts_count.toString(), numVal: REAL_RBK_KPI.mes.alerts_count, sub:"⚠ Requieren atención", subC:"c-red", valC:"c-red", trend:[30,35,32,38,40,39,REAL_RBK_KPI.mes.alerts_count], lineC:"#f87171", type:"alert",
              alerts: REAL_RBK_KPI.mes.alert_list }
        ]
    },
    on: {
        hoy: [
            { tit:"FILL RATE GLOBAL", val: REAL_ON_KPI.hoy.fill.toFixed(1)+"%", numVal: REAL_ON_KPI.hoy.fill, sub:"Surtido de hoy", subC:"c-muted", valC:"c-pink", trend:[78,80,79,81,80,82,REAL_ON_KPI.hoy.fill], lineC:"#f472b6", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val: REAL_ON_KPI.hoy.vol.toLocaleString(), numVal: REAL_ON_KPI.hoy.vol, sub:"Unidades hoy", subC:"c-muted", valC:"c-amber", trend:[3500,3400,3200,3000,2900,3050,REAL_ON_KPI.hoy.vol], lineC:"#fbbf24", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS", val: REAL_ON_KPI.hoy.alerts_count.toString(), numVal: REAL_ON_KPI.hoy.alerts_count, sub:"⚠ Requieren atención", subC:"c-red", valC:"c-red", trend:[5,6,8,7,9,6,REAL_ON_KPI.hoy.alerts_count], lineC:"#f87171", type:"alert",
              alerts: REAL_ON_KPI.hoy.alert_list }
        ],
        semana: [
            { tit:"FILL RATE GLOBAL", val: REAL_ON_KPI.semana.fill.toFixed(1)+"%", numVal: REAL_ON_KPI.semana.fill, sub:"Últimos 7 días", subC:"c-muted", valC:"c-pink", trend:[72,74,76,75,78,79,REAL_ON_KPI.semana.fill], lineC:"#f472b6", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val: REAL_ON_KPI.semana.vol.toLocaleString(), numVal: REAL_ON_KPI.semana.vol, sub:"Unidades esta semana", subC:"c-muted", valC:"c-amber", trend:[22000,21000,20500,19800,19500,19700,REAL_ON_KPI.semana.vol], lineC:"#fbbf24", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS", val: REAL_ON_KPI.semana.alerts_count.toString(), numVal: REAL_ON_KPI.semana.alerts_count, sub:"⚠ Requieren atención", subC:"c-red", valC:"c-red", trend:[18,20,15,22,25,21,REAL_ON_KPI.semana.alerts_count], lineC:"#f87171", type:"alert",
              alerts: REAL_ON_KPI.semana.alert_list }
        ],
        mes: [
            { tit:"FILL RATE GLOBAL", val: REAL_ON_KPI.mes.fill.toFixed(1)+"%", numVal: REAL_ON_KPI.mes.fill, sub:"Últimos 30 días", subC:"c-muted", valC:"c-pink", trend:[68,70,72,73,75,74,REAL_ON_KPI.mes.fill], lineC:"#f472b6", type:"fill" },
            { tit:"VOLUMEN PROCESADO", val: REAL_ON_KPI.mes.vol.toLocaleString(), numVal: REAL_ON_KPI.mes.vol, sub:"Unidades este mes", subC:"c-muted", valC:"c-amber", trend:[95000,92000,88000,85000,84500,84200,REAL_ON_KPI.mes.vol], lineC:"#fbbf24", type:"vol" },
            { tit:"ÓRDENES CRÍTICAS", val: REAL_ON_KPI.mes.alerts_count.toString(), numVal: REAL_ON_KPI.mes.alerts_count, sub:"⚠ Requieren atención", subC:"c-red", valC:"c-red", trend:[40,45,48,50,54,55,REAL_ON_KPI.mes.alerts_count], lineC:"#f87171", type:"alert",
              alerts: REAL_ON_KPI.mes.alert_list }
        ]
    }
};

let state = { rbk: { view:0, filter:'semana' }, on: { view:0, filter:'semana' } };

function makeSVG(data, color) {
    if (!data || data.length === 0) return '';
    const W=480, H=65;
    const mx=Math.max(...data)*1.05, mn=Math.min(...data)*0.95, rng=Math.max(mx-mn, 1);
    const pts=data.map((v,i)=>[(i/(data.length-1||1))*W, H-((v-mn)/rng)*H]);
    const pathD=pts.map((p,i)=>(i===0?'M':'L')+p[0]+' '+p[1]).join(' ');
    const fillD=pathD+' L '+W+' '+H+' L 0 '+H+' Z';
    const uid='s'+Math.floor(Math.random()*10000);
    const circles=pts.map(p=>'<circle cx="'+p[0]+'" cy="'+p[1]+'" r="3.5" fill="'+color+'" stroke="#161c28" stroke-width="2"/>').join('');
    return '<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" style="width:100%;height:75px;overflow:visible;">'+
        '<defs><linearGradient id="'+uid+'" x1="0" x2="0" y1="0" y2="1">'+
        '<stop offset="0%" stop-color="'+color+'" stop-opacity="0.18"/>'+
        '<stop offset="100%" stop-color="'+color+'" stop-opacity="0.0"/></linearGradient>'+
        '<filter id="gl'+uid+'"><feGaussianBlur stdDeviation="2"/></filter></defs>'+
        '<path d="'+fillD+'" fill="url(#'+uid+')"/>'+
        '<path d="'+pathD+'" fill="none" stroke="'+color+'" stroke-width="2" opacity="0.25" filter="url(#gl'+uid+')"/>'+
        '<path d="'+pathD+'" fill="none" stroke="'+color+'" stroke-width="2"/>'+
        circles+'</svg>';
}

function render(acc) {
    try {
        const s=state[acc], d=DATA[acc][s.filter][s.view];
        const dotC=acc==='rbk'?'blue':'pink';
        const total=DATA[acc][s.filter].length;
        const isAlert = d.type === 'alert';
        
        let kpiHtml = '<div class="kpi-title">'+d.tit+'</div>'+
            '<div class="kpi-val '+d.valC+(isAlert?' clickable':'')+'" '+(isAlert?'onclick="toggleAlertDetail(\\''+acc+'\\')" title="Click para ver detalles"':'')+'>'+d.val+'</div>'+
            '<div class="kpi-sub '+d.subC+'">'+d.sub+'</div>'+
            '<div class="spark-wrap">'+makeSVG(d.trend, d.lineC)+'</div>'+
            '<div id="alert-detail-'+acc+'" style="display:none;"></div>';

        document.getElementById('kpi-'+acc).innerHTML = kpiHtml;

        let dots='';
        for(let i=0;i<total;i++) dots+='<div class="dot '+(i===s.view?'active '+dotC:'')+'"></div>';
        document.getElementById('dots-'+acc).innerHTML = dots;

        // Update Pill Status
        const alerts_count = DATA[acc][s.filter][2].numVal;
        const pill = document.getElementById('pill-' + acc);
        if (pill) {
            if (alerts_count === 0) {
                pill.className = 'pill pill-green';
                pill.innerHTML = '● OPTIMAL';
            } else if (alerts_count < 10) {
                pill.className = 'pill pill-amber';
                pill.innerHTML = '⚠ WARNING';
            } else {
                pill.className = 'pill pill-red';
                pill.innerHTML = '✖ CRITICAL';
            }
        }
        
        updateGlobalStrip();
    } catch(err) {
        console.error("Render Error:", err);
        throw err;
    }
}

function navCard(acc, dir) {
    const total=DATA[acc][state[acc].filter].length;
    state[acc].view = (state[acc].view+dir+total)%total;
    render(acc);
}

function setFilter(acc, filter, el) {
    state[acc].filter = filter;
    state[acc].view = 0;
    el.parentElement.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));
    el.classList.add('active');
    render(acc);
}

function updateGlobalStrip() {
    try {
        const rbkFill = DATA.rbk[state.rbk.filter][0].numVal;
        const onFill  = DATA.on[state.on.filter][0].numVal;
        const avgFill = ((rbkFill + onFill)/2).toFixed(1);

        const rbkVol = DATA.rbk[state.rbk.filter][1].numVal;
        const onVol  = DATA.on[state.on.filter][1].numVal;
        const totalVol = (rbkVol + onVol).toLocaleString();

        const rbkAlerts = DATA.rbk[state.rbk.filter][2].numVal;
        const onAlerts  = DATA.on[state.on.filter][2].numVal;
        const totalAlerts = rbkAlerts + onAlerts;

        const elFill = document.getElementById('gs-fill');
        const elVol = document.getElementById('gs-vol');
        const elAlerts = document.getElementById('gs-alerts');
        
        if(elFill) elFill.textContent = avgFill + '%';
        if(elVol) elVol.textContent = totalVol;
        if(elAlerts) elAlerts.textContent = totalAlerts;
    } catch(err) {
        console.error("Global Strip Error:", err);
        throw err;
    }
}

function toggleAlertDetail(acc) {
    const el = document.getElementById('alert-detail-'+acc);
    if (el.style.display === 'none') {
        const d = DATA[acc][state[acc].filter][state[acc].view];
        if (!d.alerts) return;
        let html = '<div class="alert-detail"><strong>Detalle de Alertas:</strong>';
        d.alerts.forEach(a => {
            html += '<div class="alert-row"><span><strong>'+a.qty+'</strong> — '+a.client+'</span><span style="color:#f87171;">'+a.status+'</span></div>';
        });
        html += '</div>';
        el.innerHTML = html;
        el.style.display = 'block';
    } else {
        el.style.display = 'none';
    }
}

function enterDashboard(acc) {
    const label = acc === 'reebok' ? 'Dashboard Reebok' : 'Dashboard ON';
    try {
        const parentDoc = window.parent.document;
        const entries = Array.from(parentDoc.querySelectorAll('button, a, [role="button"], span'));
        const target = entries.find(el => el.textContent.trim().toLowerCase() === label.toLowerCase());
        if (target) {
            target.click();
            return;
        }
    } catch(e) {}
    const slug = label.replace(/\s+/g, '_');
    window.open(window.location.origin + '/' + slug, '_top');
}




function showGlobalAlerts() {
    const modal = document.getElementById('global-alert-modal');
    if (modal.style.display === 'flex') { modal.style.display = 'none'; return; }
    modal.style.display = 'flex';

    const rbkData = DATA.rbk[state.rbk.filter][2];
    const onData  = DATA.on[state.on.filter][2];

    let html = '';
    html += '<div style="padding-right:20px;"><div style="font-weight:600; color:#38bdf8; margin-bottom:12px; font-size:13px; letter-spacing:1px;">Reebok ('+rbkData.numVal+' alertas)</div>';
    (rbkData.alerts||[]).forEach(a => {
        let info = '<div style="margin-bottom:10px; padding-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.05);">';
        info += '<div style="font-weight:500; color:#f1f5f9; margin-bottom:3px;">'+a.client+'</div>';
        if (a.doc) info += '<div style="font-size:11px; color:rgba(255,255,255,0.4);">Doc: <span style="color:rgba(255,255,255,0.65);">'+a.doc+'</span></div>';
        if (a.ref) info += '<div style="font-size:11px; color:rgba(255,255,255,0.4);">Ref: <span style="color:rgba(255,255,255,0.65);">'+a.ref+'</span></div>';
        info += '<div style="font-size:11px; color:#f87171; margin-top:3px;">'+a.status+'</div></div>';
        html += info;
    });
    html += '</div>';
    html += '<div style="background:rgba(255,255,255,0.06); width:1px;"></div>';
    html += '<div style="padding-left:20px;"><div style="font-weight:600; color:#f472b6; margin-bottom:12px; font-size:13px; letter-spacing:1px;">ON ('+onData.numVal+' alertas)</div>';
    (onData.alerts||[]).forEach(a => {
        html += '<div class="alert-row"><span><strong>'+a.qty+'</strong> — '+a.client+'</span><span style="color:#f87171;">'+a.status+'</span></div>';
    });
    html += '</div>';

    document.getElementById('global-alert-content').innerHTML = html;
    modal.style.display = 'flex';
}

// ── INIT ──
document.addEventListener("DOMContentLoaded", function() {
    render('rbk');
    render('on');
});
</script>
</body>
</html>
"""

logo_b64 = get_base64_of_bin_file("assets/logo.png")
sync_time = datetime.now(CDMX_TZ).strftime("%H:%M")
html_rendered = hub_html.replace('<!--DATA_ON-->', json.dumps(real_on)) \
                        .replace('<!--DATA_RBK-->', json.dumps(real_rbk)) \
                        .replace('<!--LOGO_B64-->', logo_b64) \
                        .replace('<!--LAST_SYNC-->', f"Hoy a las {sync_time}")

components.html(html_rendered, height=850, scrolling=False)
