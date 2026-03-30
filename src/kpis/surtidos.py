"""
surtidos.py — KPIs de Outbound (Surtidos).
Incluye el motor de status derivado (_derive_status), KPIs core, chart data
y la nueva batería de KPIs outbound.
"""
import pandas as pd
import numpy as np
from datetime import datetime
import streamlit as st
import pytz
from src.kpis.helpers import clean_comparable_dates, clean_numeric_percent, clean_numeric

# Configuración Horaria
CDMX_TZ = pytz.timezone('America/Mexico_City')

# Exportar explícitamente _derive_status (el underscore lo excluye de import *)
__all__ = [
    'calculate_fill_rate', 'calculate_otd', 'calculate_pipeline_status',
    '_derive_status',
    'get_orders_by_client', 'get_status_distribution', 'get_otd_by_client',
    'get_weekly_throughput', 'get_pipeline_funnel',
    'get_pct_surtido', 'get_avance_etapa', 'get_cumplimiento_entrega',
    'get_backlog', 'get_volumen_surtido', 'get_audit_quality',
    'get_wip_metrics', 'get_desempeno_cliente',
]


# ============================================
# CORE KPIs (Scalar Values)
# ============================================

def calculate_fill_rate(df_surtidos):
    """Only count rows where TOTAL DE PIEZAS > 0."""
    df = df_surtidos.copy()
    df['total'] = clean_numeric(df, 'TOTAL DE PIEZAS')
    df['picked'] = clean_numeric(df, 'PIEZAS SURTIDAS')
    # Filter out rows with 0 or blank total
    valid = df[df['total'] > 0]
    if valid.empty: return 0.0
    total = valid['total'].sum()
    picked = valid['picked'].sum()
    if total == 0: return 0.0
    return picked / total

def calculate_otd(df_surtidos):
    """Uses '% EN PROCESO COMPLETO' column if available, otherwise uses dates."""
    df = df_surtidos.copy()
    
    # Try to use '% EN PROCESO COMPLETO' column first
    pct_col = '% EN PROCESO COMPLETO'
    if pct_col in df.columns:
        df['pct_completo'] = clean_numeric_percent(df, pct_col)
        # Filter out blanks and zeros - only count real data
        valid = df[df['pct_completo'] > 0].copy()
        if not valid.empty:
            valid['on_time'] = valid['pct_completo'] >= 1.0  # 100% = on time
            return valid['on_time'].mean(), valid
    
    # Fallback to date comparison
    if 'FECHA / HORA ENTREGADO' in df.columns:
        df['dt_ent'] = clean_comparable_dates(df, 'FECHA / HORA ENTREGADO')
    else:
        df['dt_ent'] = clean_comparable_dates(df, 'FECHA ENTREGADO')
    df['dt_prom'] = clean_comparable_dates(df, 'FECHA A ENTREGAR')
    valid = df.dropna(subset=['dt_ent', 'dt_prom'])
    if valid.empty: return 0.0, pd.DataFrame()
    valid['on_time'] = valid['dt_ent'] <= valid['dt_prom']
    return valid['on_time'].mean(), valid

def calculate_pipeline_status(df_surtidos):
    df = df_surtidos.copy()
    stage_map = {'Surtido': '%', 'Etiquetado': '%.1', 'Distribucion': '%.2', 'Auditoria': '%.3'}
    results = {}
    for stage, col in stage_map.items():
        series = clean_numeric_percent(df, col)
        results[stage] = series.mean()
    return results


# ============================================
# STATUS DERIVATION ENGINE
# ============================================

def _derive_status(df):
    """
    Derives the Calculate_Status column based on business logic.
    Priority:
    1. 'ENTREGADO' if 'FECHA / HORA ENTREGADO' has a valid date.
    2. 'LISTO PARA EMBARQUE' if progress >= 99%
    3. 'DEMORADO' if not delivered and past promise date.
    4. 'EN PROCESO' otherwise.
    """
    df = df.copy()
    now = datetime.now(CDMX_TZ).replace(tzinfo=None)
    
    # 1. Clean Dates
    
    # --- COMBINE DATE + TIME for Promise Date ---
    df['dt_prom_date'] = clean_comparable_dates(df, 'FECHA A ENTREGAR')
    
    # Try to parse time if column exists
    if 'HORA A ENTREGAR' in df.columns:
        # Clean time column: force string, strip, pad 0s if needed, handle various formats
        def parse_time_str(t_str):
            if pd.isna(t_str) or str(t_str).strip() == '':
                return None
            s = str(t_str).strip()
            # Try some common formats
            for fmt in ['%H:%M:%S', '%H:%M', '%I:%M %p']:
                try:
                    return datetime.strptime(s, fmt).time()
                except:
                    pass
            return None

        time_objs = df['HORA A ENTREGAR'].apply(parse_time_str)
        
        # Combine valid date + valid time
        # Where time is NaT, default to 23:59:59 (End of Day)
        def combine_dt(row):
            d = row['dt_prom_date']
            t = row['time_obj']
            if pd.isna(d): return pd.NaT
            if t is None: return d.replace(hour=23, minute=59, second=59)
            return datetime.combine(d.date(), t)
            
        df['time_obj'] = time_objs
        df['dt_promesa'] = df.apply(combine_dt, axis=1)
        # Drop temp cols
        df = df.drop(columns=['time_obj', 'dt_prom_date'])
    else:
        # Fallback to just date (End of Day)
        df['dt_promesa'] = clean_comparable_dates(df, 'FECHA A ENTREGAR')
        df['dt_promesa'] = df['dt_promesa'].apply(lambda x: x.replace(hour=23, minute=59, second=59) if pd.notna(x) else x)

    # NEW LOGIC: Use 'FECHA / HORA ENTREGADO' as the source of truth for completion
    if 'FECHA / HORA ENTREGADO' in df.columns:
        df['dt_entregado'] = pd.to_datetime(df['FECHA / HORA ENTREGADO'], dayfirst=True, errors='coerce')
    else:
        # Fallback to old column if new one doesn't exist yet
        df['dt_entregado'] = clean_comparable_dates(df, 'FECHA ENTREGADO')
        
    # 2. Calculate Progress
    df['total_pzas'] = clean_numeric(df, 'TOTAL DE PIEZAS')
    df['surtido_pzas'] = clean_numeric(df, 'PIEZAS SURTIDAS')
    
    # Avoid division by zero
    df['progress'] = 0.0
    mask_nonzero = df['total_pzas'] > 0
    if mask_nonzero.any():
        df.loc[mask_nonzero, 'progress'] = (df.loc[mask_nonzero, 'surtido_pzas'] / df.loc[mask_nonzero, 'total_pzas']) * 100
    
    # 3. Define Status
    def get_row_status(row):
        # A. If it has a delivery timestamp, it is DONE.
        if pd.notna(row.get('dt_entregado')):
            return 'ENTREGADO'
            
        # B. If progress >= 99%, it is READY
        if row['progress'] >= 99:
            return 'LISTO PARA EMBARQUE'
            
        # C. If past promise date, it is DELAYED
        if pd.notna(row.get('dt_promesa')) and row['dt_promesa'] < now:
            return 'DEMORADO'
            
        return 'EN PROCESO'
    
    df['Calculated_Status'] = df.apply(get_row_status, axis=1)
    
    # 4. Define On-Time flag (for completed orders)
    def is_on_time_logic(row):
        actual = row.get('dt_entregado')
        promised = row.get('dt_promesa')
        
        if pd.isna(actual):
            return 0 # Not delivered yet
            
        if pd.isna(promised):
            return 1 # Delivered but no promise date? Assume on time.
            
        # FIX: If promise has no time/is midnight, set it to END of day (23:59:59) for fair comparison
        if promised.hour == 0 and promised.minute == 0:
            promised = promised.replace(hour=23, minute=59, second=59)
            
        return 1 if actual <= promised else 0

    df['on_time'] = df.apply(is_on_time_logic, axis=1)
    
    return df


# ============================================
# CHART DATA - SURTIDOS
# ============================================

@st.cache_data(ttl=300, show_spinner=False)
def get_orders_by_client(df_surtidos):
    """Orders aggregated by client."""
    if df_surtidos.empty:
        return pd.DataFrame()
    
    df = df_surtidos.copy()
    if 'CLIENTE' not in df.columns:
        return pd.DataFrame()
    
    df['Piezas'] = clean_numeric(df, 'TOTAL DE PIEZAS')
    # Filter out 0 pieces
    df = df[df['Piezas'] > 0]
    
    grouped = df.groupby('CLIENTE').agg(
        Total_Piezas=('Piezas', 'sum'),
        Ordenes=('CLIENTE', 'count')
    ).reset_index().sort_values('Total_Piezas', ascending=False)
    return grouped

@st.cache_data(ttl=300, show_spinner=False)
def get_status_distribution(df_surtidos):
    """Distribution using DERIVED Status from dates/progress."""
    if df_surtidos.empty:
        return pd.DataFrame()
    
    df = _derive_status(df_surtidos)
    
    if 'Calculated_Status' not in df.columns:
        return pd.DataFrame()

    # Filter out empty computations ensuring we have valid rows
    # Removing rows with no status or empty string
    df = df[df['Calculated_Status'].notna() & (df['Calculated_Status'] != '')]
    
    # Also filter out rows with 0 total pieces (invalid orders) if not already done
    if 'TOTAL DE PIEZAS' in df.columns:
        df['temp_pzas'] = clean_numeric(df, 'TOTAL DE PIEZAS')
        df = df[df['temp_pzas'] > 0]

    counts = df['Calculated_Status'].value_counts().reset_index()
    counts.columns = ['Status', 'Cantidad']
    return counts

@st.cache_data(ttl=300, show_spinner=False)
def get_otd_by_client(df_surtidos):
    """OTD performance per client for scatter."""
    df = df_surtidos.copy()
    if 'CLIENTE' not in df.columns:
        return pd.DataFrame()
    
    if 'FECHA / HORA ENTREGADO' in df.columns:
        df['dt_ent'] = clean_comparable_dates(df, 'FECHA / HORA ENTREGADO')
    else:
        df['dt_ent'] = clean_comparable_dates(df, 'FECHA ENTREGADO')
    df['dt_prom'] = clean_comparable_dates(df, 'FECHA A ENTREGAR')
    df['on_time'] = (df['dt_ent'] <= df['dt_prom']).astype(int)
    df['Piezas'] = clean_numeric(df, 'TOTAL DE PIEZAS')
    df['Surtidas'] = clean_numeric(df, 'PIEZAS SURTIDAS')
    df['fill'] = np.where(df['Piezas'] > 0, df['Surtidas'] / df['Piezas'], 0)
    
    grouped = df.groupby('CLIENTE').agg(
        OTD=('on_time', 'mean'),
        Fill_Rate=('fill', 'mean'),
        Volumen=('Piezas', 'sum')
    ).reset_index()
    return grouped

@st.cache_data(ttl=300, show_spinner=False)
def get_weekly_throughput(df_surtidos):
    """Weekly orders and OTD using SEMANA column."""
    df = df_surtidos.copy()
    if 'SEMANA' not in df.columns:
        return pd.DataFrame()
    
    # Use correct delivery column (same as _derive_status)
    if 'FECHA / HORA ENTREGADO' in df.columns:
        df['dt_ent'] = pd.to_datetime(df['FECHA / HORA ENTREGADO'], dayfirst=True, errors='coerce')
    else:
        df['dt_ent'] = clean_comparable_dates(df, 'FECHA ENTREGADO')
    
    df['dt_prom'] = clean_comparable_dates(df, 'FECHA A ENTREGAR')
    
    # Only compare when both dates are valid; NaN = not delivered = exclude from OTD
    both_valid = df['dt_ent'].notna() & df['dt_prom'].notna()
    df['on_time'] = np.nan  # Default NaN (not counted)
    df.loc[both_valid, 'on_time'] = (df.loc[both_valid, 'dt_ent'] <= df.loc[both_valid, 'dt_prom']).astype(int)
    
    df['surtido_pzas'] = clean_numeric(df, 'PIEZAS SURTIDAS')
    df['SEMANA'] = clean_numeric(df, 'SEMANA')
    df = df[df['SEMANA'] > 0]
    
    grouped = df.groupby('SEMANA').agg(
        Ordenes=('CLIENTE', 'count'),
        Surtido=('surtido_pzas', 'sum'),
        OTD=('on_time', 'mean')
    ).reset_index()
    
    # Fill NaN OTD (weeks with no deliveries) with 0
    grouped['OTD'] = grouped['OTD'].fillna(0)
    
    return grouped

@st.cache_data(ttl=300, show_spinner=False)
def get_pipeline_funnel(df_surtidos):
    """Funnel data for pipeline stages."""
    if df_surtidos.empty:
        return pd.DataFrame()
    
    pipeline = calculate_pipeline_status(df_surtidos)
    total = clean_numeric(df_surtidos, 'TOTAL DE PIEZAS').sum()
    
    # Handle empty/NaN total
    if pd.isna(total) or total == 0:
        return pd.DataFrame()
    
    data = []
    stages = ['Solicitado', 'Surtido', 'Etiquetado', 'Distribuido', 'Auditado']
    multipliers = [1.0, pipeline.get('Surtido', 0), pipeline.get('Etiquetado', 0), 
                   pipeline.get('Distribucion', 0), pipeline.get('Auditoria', 0)]
    
    for stage, mult in zip(stages, multipliers):
        # Handle NaN multipliers
        mult = 0 if pd.isna(mult) else mult
        data.append({'Etapa': stage, 'Piezas': int(total * mult), 'Porcentaje': f"{mult*100:.1f}%"})
    
    return pd.DataFrame(data)


# ============================================
# NEW KPIs - OUTBOUND (SURTIDOS)
# ============================================

@st.cache_data(ttl=300, show_spinner=False)
def get_pct_surtido(df_surtidos):
    """
    % Surtido - Fill rate percentage (AVERAGE PER ORDER).
    Calculates: Average of (Surtido_i / Total_i) for each order.
    Each order counts equally regardless of size.
    Only counts 'ENTREGADO' or 'LISTO PARA EMBARQUE'.
    """
    if df_surtidos.empty:
        return {'pct': 0, 'surtido': 0, 'total': 0, 'pendiente': 0, 'ordenes_validas': 0}
        
    df = _derive_status(df_surtidos)
    # Filter: Only Completed or Ready (exclude WIP)
    valid = df[df['Calculated_Status'].isin(['ENTREGADO', 'LISTO PARA EMBARQUE'])].copy()
    
    if valid.empty:
        return {'pct': 0, 'surtido': 0, 'total': 0, 'pendiente': 0, 'ordenes_validas': 0}
        
    # Ensure columns are numeric
    valid['total_pzas'] = clean_numeric(valid, 'TOTAL DE PIEZAS')
    valid['surtido_pzas'] = clean_numeric(valid, 'PIEZAS SURTIDAS')
    
    # Filter out orders with 0 total pieces (can't calculate %)
    valid = valid[valid['total_pzas'] > 0].copy()
    
    if valid.empty:
        return {'pct': 0, 'surtido': 0, 'total': 0, 'pendiente': 0, 'ordenes_validas': 0}
    
    # AVERAGE PER ORDER: Calculate each order's fill rate, then average
    valid['order_fill_rate'] = (valid['surtido_pzas'] / valid['total_pzas'] * 100).clip(0, 100)
    pct = valid['order_fill_rate'].mean()
    
    # Also return totals for reference
    total = valid['total_pzas'].sum()
    surtido = valid['surtido_pzas'].sum()
    
    return {
        'pct': pct, 
        'surtido': surtido, 
        'total': total, 
        'pendiente': total - surtido,
        'ordenes_validas': len(valid)
    }

@st.cache_data(ttl=300, show_spinner=False)
def get_avance_etapa(df_surtidos):
    """Avance por etapa - Progress through pipeline stages. Only counts non-zero rows."""
    df = df_surtidos.copy()
    
    # Count only rows that have any progress (not all zeros)
    df['has_progress'] = (
        clean_numeric_percent(df, '%') + 
        clean_numeric_percent(df, '%.1') + 
        clean_numeric_percent(df, '%.2') + 
        clean_numeric_percent(df, '%.3')
    ) > 0
    valid = df[df['has_progress']]
    
    if valid.empty:
        return {'surtido': 0, 'etiquetado': 0, 'distribucion': 0, 'auditoria': 0, 'total_ordenes': 0}
    
    # Calculate averages only for valid rows
    surtido = clean_numeric_percent(valid, '%').mean() * 100
    etiquetado = clean_numeric_percent(valid, '%.1').mean() * 100
    distribucion = clean_numeric_percent(valid, '%.2').mean() * 100
    auditoria = clean_numeric_percent(valid, '%.3').mean() * 100
    
    return {
        'surtido': surtido,
        'etiquetado': etiquetado,
        'distribucion': distribucion,
        'auditoria': auditoria,
        'total_ordenes': len(valid)
    }

@st.cache_data(ttl=300, show_spinner=False)
def get_cumplimiento_entrega(df_surtidos):
    """
    Cumplimiento entrega - On-time delivery. 
    Only counts 'ENTREGADO'. 'LISTO' doesn't count until actually delivered for OTD.
    """
    if df_surtidos.empty:
        return {'pct': 0, 'on_time': 0, 'late': 0, 'total': 0}
        
    df = _derive_status(df_surtidos)
    # Strict OTD: Only what is actually delivered
    valid = df[df['Calculated_Status'] == 'ENTREGADO'].copy()
    
    if valid.empty:
        return {'pct': 0, 'on_time': 0, 'late': 0, 'total': 0}
        
    # Reuse cleaned dates from _derive_status (which now has 'dt_entregado' and 'dt_promesa')
    # If dt_promesa has time, we use it for precise comparison.
    
    # Check on time
    # Note: _derive_status already cleaned 'dt_entregado' and computed 'on_time' logic
    # We can just reuse the 'on_time' column if it exists, or recalculate carefully
    
    if 'on_time' in valid.columns:
        on_time = valid['on_time'].sum()
    else:
        # Fallback if on_time col missing for some reason
        prom = valid['dt_promesa'] if 'dt_promesa' in valid.columns else clean_comparable_dates(valid, 'FECHA A ENTREGAR')
        ent = valid['dt_entregado']
        
        # Ensure prom has time if missing (end of day) - logic consistent with _derive_status
        # But really we should trust _derive_status to have done this.
        on_time_mask = ent <= prom
        on_time = on_time_mask.sum()

    total = len(valid)
    
    return {'pct': (on_time / total * 100) if total > 0 else 0, 'on_time': on_time, 'late': total - on_time, 'total': total}

@st.cache_data(ttl=300, show_spinner=False)
def get_backlog(df_surtidos):
    """Backlog - Orders pending or delayed using DERIVED logic."""
    if df_surtidos.empty:
        return {'pendiente': 0, 'en_proceso': 0, 'completado': 0, 'total': 0, 'all_status': {}, 'display_backlog': 0, 'critical': 0, 'on_track': 0}
    
    # Use computed status
    df = _derive_status(df_surtidos)
    status_counts = df['Calculated_Status'].value_counts().to_dict()
    
    # Map computed statuses to backlog buckets
    completado = status_counts.get('ENTREGADO', 0)
    listo_embarque = status_counts.get('LISTO PARA EMBARQUE', 0)
    en_proceso = status_counts.get('EN PROCESO', 0)
    pendiente = status_counts.get('PENDIENTE', 0)
    
    # Check for Critical within NON-COMPLETED
    # Critical if FECHA A ENTREGAR < Today AND Status != ENTREGADO
    critical = 0
    if 'FECHA A ENTREGAR' in df.columns:
        today = datetime.now(CDMX_TZ).replace(tzinfo=None) # Keep naive for clean_comparable_dates column comparison if they are naive
        df['dt_prom'] = clean_comparable_dates(df, 'FECHA A ENTREGAR')
        
        # Critical: Not Delivered AND Promise Date Passed
        # Note: 'LISTO PARA EMBARQUE' might be critical if it hasn't shipped by promise date!
        mask_critical = (df['Calculated_Status'] != 'ENTREGADO') & \
                        (df['dt_prom'].notna()) & \
                        (df['dt_prom'] < today)
        critical = len(df[mask_critical])

    # On Track: In Process/Ready/Pending but NOT late
    on_track = (en_proceso + pendiente + listo_embarque) - critical
    
    # Display Backlog: Total output that needs attention (Pending + Process + Ready)
    display_backlog = pendiente + en_proceso + listo_embarque

    return {
        'pendiente': pendiente,
        'en_proceso': en_proceso, # Includes 'LISTO PARA EMBARQUE' in generic bucket? Or separate? 
                                 # Let's keep strict to what was asked. 
                                 # User might want to see 'LISTO' separate.
                                 # For simplicity matching UI: 'en_proceso' usually implies active work.
                                 # 'encurso' vs 'pendiente'.
        'critical': critical,
        'on_track': max(0, on_track),
        'display_backlog': display_backlog,
        'completado': completado,
        'total': len(df),
        'all_status': status_counts # Pass full dict for charts
    }

@st.cache_data(ttl=300, show_spinner=False)
def get_volumen_surtido(df_surtidos):
    """Volumen surtido - Total volume picked/shipped. Only counts valid data."""
    df = df_surtidos.copy()
    df['total_pzas'] = clean_numeric(df, 'TOTAL DE PIEZAS')
    df['surtido_pzas'] = clean_numeric(df, 'PIEZAS SURTIDAS')
    
    # Filter out rows with no data (blank totals and zeros)
    valid = df[df['total_pzas'] > 0]
    
    if valid.empty:
        return {'total': 0, 'surtido': 0, 'ordenes': 0, 'by_week': []}
    
    total = valid['total_pzas'].sum()
    surtido = valid['surtido_pzas'].sum()
    ordenes = len(valid)
    
    # By week if available
    by_week = []
    if 'SEMANA' in valid.columns:
        valid['SEMANA'] = clean_numeric(valid, 'SEMANA')
        valid_weeks = valid[valid['SEMANA'] > 0]
        if not valid_weeks.empty:
            weekly = valid_weeks.groupby('SEMANA').agg(
                Surtido=('surtido_pzas', 'sum'),
                Ordenes=('CLIENTE', 'count')
            ).reset_index()
            weekly['AvgTicket'] = (weekly['Surtido'] / weekly['Ordenes']).round(0)
            by_week = weekly.to_dict('records')
    
    return {'total': total, 'surtido': surtido, 'ordenes': ordenes, 'by_week': by_week}

@st.cache_data(ttl=300, show_spinner=False)
def get_audit_quality(df_surtidos):
    """
    Outbound KPI: Audit/Compliance Quality Score.
    Uses Column T (% CUMPLIMIENTO or total compliance %) directly.
    """
    df = df_surtidos.copy()
    
    # Priority: Look for total compliance column (Column T/V)
    # User confirmed: '% EN PROCESO COMPLETO'
    possible_names = ['% EN PROCESO COMPLETO', '% CUMPLIMIENTO', 'CUMPLIMIENTO TOTAL', 'TOTAL %']
    col_cumpl = None
    
    for name in possible_names:
        if name in df.columns:
            col_cumpl = name
            break
    
    # OLD FALLBACK REMOVED: df.columns[19] is no longer safe due to column shifts.
    # We rely on finding the name.
    
    if col_cumpl is None:
        # Last fallback: use old logic with %.3 (Audit %)
        col_cumpl = '%.3' if '%.3' in df.columns else None
    
    if col_cumpl is None or col_cumpl not in df.columns:
        return {'pct': 0.0, 'passed': 0, 'total': 0, 'col_used': 'N/A'}
    
    # Filter for Completed/Ready only
    df = _derive_status(df)
    valid_status = df[df['Calculated_Status'].isin(['ENTREGADO', 'LISTO PARA EMBARQUE'])].copy()
    
    if valid_status.empty:
         return {'pct': 0.0, 'passed': 0, 'total': 0, 'col_used': col_cumpl, 'breakdown': {}}

    vals = clean_numeric_percent(valid_status, col_cumpl)
    # Include ALL values (including 0%) - if it has data, it counts
    valid_vals = vals.dropna()
    
    # Count "passed" as those with 100% or higher compliance
    passed = len(valid_vals[valid_vals >= 1.0])
    
    # Create breakdown of non-100% values
    incomplete = valid_vals[valid_vals < 1.0]
    breakdown = (incomplete * 100).round(1).value_counts().sort_index().to_dict()
    
    if len(valid_vals) == 0:
        return {'pct': 0.0, 'passed': 0, 'total': 0, 'col_used': col_cumpl, 'breakdown': {}}
        
    return {
        'pct': valid_vals.mean() * 100,
        'passed': passed,
        'total': len(valid_vals),
        'col_used': col_cumpl,
        'breakdown': {f"{k}%": v for k, v in breakdown.items()}
    }

@st.cache_data(ttl=300, show_spinner=False)
def get_wip_metrics(df_surtidos):
    """
    NEW: Metrics for Active/In-Process orders only.
    Returns: Average progress %, Pending pieces, Count of orders.
    """
    if df_surtidos.empty:
        return {'avance': 0, 'piezas_pendientes': 0, 'ordenes': 0, 'total_piezas': 0}
        
    df = _derive_status(df_surtidos)
    
    # Filter: EN PROCESO or PENDIENTE
    # (Users often want to see 'Pendiente' here too as 'To Do')
    # Let's strictly use 'EN PROCESO' for progress avg, but 'PENDIENTE' adds to volume.
    wip = df[df['Calculated_Status'].isin(['EN PROCESO', 'PENDIENTE'])].copy()
    
    if wip.empty:
        return {'avance': 0, 'piezas_pendientes': 0, 'ordenes': 0, 'total_piezas': 0}
        
    # Calculate pieces
    wip['total_pzas'] = clean_numeric(wip, 'TOTAL DE PIEZAS')
    wip['surtido_pzas'] = clean_numeric(wip, 'PIEZAS SURTIDAS')
    
    total_expected = wip['total_pzas'].sum()
    total_done = wip['surtido_pzas'].sum()
    pending = total_expected - total_done
    
    # Calculate average progress of ACTIVE orders only (exclude strict pending 0%)
    active = wip[wip['Calculated_Status'] == 'EN PROCESO'].copy()
    avg_progress = 0
    histogram = {}
    
    if not active.empty:
        active['fill'] = np.where(active['total_pzas']>0, active['surtido_pzas']/active['total_pzas'], 0)
        avg_progress = active['fill'].mean() * 100
        
        # Calculate Histogram buckets (0-10, 11-20, etc.)
        # Bins: [0, 0.1, 0.2, ... 1.0]
        bins = [0, 0.2, 0.4, 0.6, 0.8, 1.01]
        labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-99%']
        
        # Categorize
        active['bin'] = pd.cut(active['fill'], bins=bins, labels=labels, include_lowest=True, right=False)
        histogram = active['bin'].value_counts().sort_index().to_dict()
        
    return {
        'avance': avg_progress,
        'piezas_pendientes': pending,
        'ordenes': len(active), # Count of ones actually moving
        'total_wip_count': len(wip), # Including untouched
        'distribution': histogram # New Histogram Data
    }

@st.cache_data(ttl=300, show_spinner=False)
def get_desempeno_cliente(df_surtidos):
    """Desempeño cliente - Performance metrics by client."""
    if 'CLIENTE' not in df_surtidos.columns:
        return pd.DataFrame()
    
    df = df_surtidos.copy()
    if 'FECHA / HORA ENTREGADO' in df.columns:
        df['dt_ent'] = clean_comparable_dates(df, 'FECHA / HORA ENTREGADO')
    else:
        df['dt_ent'] = clean_comparable_dates(df, 'FECHA ENTREGADO')
    df['dt_prom'] = clean_comparable_dates(df, 'FECHA A ENTREGAR')
    df['on_time'] = (df['dt_ent'] <= df['dt_prom']).astype(int)
    df['Total'] = clean_numeric(df, 'TOTAL DE PIEZAS')
    df['Surtido'] = clean_numeric(df, 'PIEZAS SURTIDAS')
    df['fill'] = np.where(df['Total'] > 0, df['Surtido'] / df['Total'], 0)
    
    grouped = df.groupby('CLIENTE').agg(
        Ordenes=('CLIENTE', 'count'),
        Piezas=('Total', 'sum'),
        OTD=('on_time', 'mean'),
        Fill_Rate=('fill', 'mean')
    ).reset_index()
    
    grouped['OTD'] = grouped['OTD'] * 100
    grouped['Fill_Rate'] = grouped['Fill_Rate'] * 100
    
    return grouped.sort_values('Piezas', ascending=False)
