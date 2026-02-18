"""
Smart Alert Engine for Dashboard ON
Detects critical conditions and generates warnings.
"""
import pandas as pd
from datetime import datetime, timedelta

def detect_sla_risk(df_entradas, date_col='FECHA DE LLEGADA', hours_threshold=72):
    """
    Detects orders approaching or exceeding SLA threshold.
    Returns list of at-risk orders.
    """
    if df_entradas.empty or date_col not in df_entradas.columns:
        return {'critical': 0, 'warning': 0, 'at_risk': []}
    
    df = df_entradas.copy()
    df['dt_llegada'] = pd.to_datetime(df[date_col], errors='coerce')
    now = datetime.now()
    
    # Calculate hours since arrival
    df['hours_elapsed'] = (now - df['dt_llegada']).dt.total_seconds() / 3600
    
    # Check if already has reported date (completed)
    if 'FECHA ENVIO DE REPORTE' in df.columns:
        df['completed'] = pd.to_datetime(df['FECHA ENVIO DE REPORTE'], errors='coerce').notna()
    else:
        df['completed'] = False
    
    # At risk: not completed and approaching/exceeding threshold
    pending = df[~df['completed'] & df['dt_llegada'].notna()]
    
    critical = pending[pending['hours_elapsed'] > hours_threshold]
    warning = pending[(pending['hours_elapsed'] > hours_threshold * 0.75) & 
                      (pending['hours_elapsed'] <= hours_threshold)]
    
    return {
        'critical': len(critical),
        'warning': len(warning),
        'at_risk': critical.head(5).to_dict('records') if not critical.empty else []
    }

def detect_kpi_changes(current_kpis, previous_kpis, threshold=0.05):
    """
    Detects KPIs that changed significantly vs threshold.
    Returns list of changed KPIs.
    """
    changes = []
    comparisons = [
        ('SLA Compliance (72h)', current_kpis.get('cumpl_72h', {}).get('pct', 0), 
         previous_kpis.get('cumpl_72h', {}).get('pct', 0)),
        ('OTIF (Perfect Deliveries)', current_kpis.get('cumpl_entrega', {}).get('pct', 0),
         previous_kpis.get('cumpl_entrega', {}).get('pct', 0)),
        ('Fulfillment Rate', current_kpis.get('audit_quality', {}).get('pct', 0),
         previous_kpis.get('audit_quality', {}).get('pct', 0))
    ]
    
    for name, current, previous in comparisons:
        if previous > 0:
            change_pct = (current - previous) / previous
            if abs(change_pct) >= threshold:
                changes.append({
                    'kpi': name,
                    'current': current,
                    'previous': previous,
                    'change_pct': change_pct * 100,
                    'type': 'improvement' if change_pct > 0 else 'drop'
                })
    
    return changes

def get_worst_performers(df_surtidos, metric_col='TOTAL DE PIEZAS', group_col='CLIENTE', n=3):
    """
    Returns bottom N performers by metric.
    """
    if df_surtidos.empty or group_col not in df_surtidos.columns:
        return []
    
    df = df_surtidos.copy()
    df[metric_col] = pd.to_numeric(df.get(metric_col, 0), errors='coerce').fillna(0)
    
    grouped = df.groupby(group_col)[metric_col].sum().reset_index()
    grouped = grouped.sort_values(metric_col, ascending=True)
    
    return grouped.head(n).to_dict('records')

def generate_alerts(df_entradas, df_surtidos, current_kpis, previous_kpis):
    """
    Master function to generate all alerts.
    """
    sla_risk = detect_sla_risk(df_entradas)
    kpi_changes = detect_kpi_changes(current_kpis, previous_kpis)
    
    alerts = []
    
    # Critical SLA alerts
    if sla_risk['critical'] > 0:
        alerts.append({
            'type': 'critical',
            'icon': '🚨',
            'message': f"{sla_risk['critical']} Pedimentos excedieron SLA 72h"
        })
        
    # KPI Changes
    for ch in kpi_changes:
        symbol = '📈' if ch['type'] == 'improvement' else '📉'
        alerts.append({
            'type': 'info',
            'icon': symbol,
            'message': f"{ch['kpi']}: {ch['current']:.1f}% ({ch['change_pct']:+.1f}%)"
        })
        
    # NEW: Detect Delayed Orders using KPI Engine Logic
    # We must import kpi_engine here to access _derive_status or replicate logic
    # To avoid circular imports, we'll try to use columns if they exist or pass derived data
    # Better approach: Check if 'Calculated_Status' exists in df_surtidos (it should if derived before)
    # If not, we can't reliably detect.
    
    # Check for direct status first (Airport Mode logic)
    delayed_count = 0
    if not df_surtidos.empty:
        # We need to know which are delayed. 
        # Since we can't easily call kpi_engine here without risk,
        # we'll implement a simple check if 'FECHA A ENTREGAR' < now and not delivered
        now = datetime.now()
        
        # Helper to parse
        def parse_dt(x):
            return pd.to_datetime(x, dayfirst=True, errors='coerce')
            
        df = df_surtidos.copy()
        df['dt_prom'] = parse_dt(df['FECHA A ENTREGAR'])
        
        # Check delivery
        if 'FECHA / HORA ENTREGADO' in df.columns:
             df['delivered'] = parse_dt(df['FECHA / HORA ENTREGADO']).notna()
        elif 'FECHA ENTREGADO' in df.columns:
             df['delivered'] = parse_dt(df['FECHA ENTREGADO']).notna()
        else:
             df['delivered'] = False
             
        # Check delay
        # Filter where prom < now AND not delivered
        delayed = df[
            (df['dt_prom'] < now) & 
            (~df['delivered']) &
            (df['dt_prom'].notna())
        ]
        delayed_count = len(delayed)
        
    if delayed_count > 0:
        alerts.append({
            'type': 'warning',
            'icon': '⚠️',
            'message': f"{delayed_count} Órdenes Demoradas (Vencidas)"
        })

    return {
        'alerts': alerts,
        'total_count': len(alerts)
    }
    
    # KPI change alerts
    for change in kpi_changes:
        icon = '📈' if change['type'] == 'improvement' else '📉'
        verb = 'mejoró' if change['type'] == 'improvement' else 'cayó'
        alerts.append({
            'type': 'info' if change['type'] == 'improvement' else 'warning',
            'icon': icon,
            'message': f"{change['kpi']} {verb} {abs(change['change_pct']):.1f}% vs semana anterior"
        })
    
    # Notification summary count
    total_alerts = len(alerts)
    
    return {
        'alerts': alerts,
        'sla_risk': sla_risk,
        'kpi_changes': kpi_changes,
        'total_count': total_alerts,
        'has_critical': any(a['type'] == 'critical' for a in alerts)
    }
