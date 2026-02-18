"""
entradas.py — KPIs de Inbound (Entradas).
Incluye KPIs core, chart data y la nueva batería de KPIs inbound.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from src.kpis.helpers import clean_comparable_dates, clean_numeric_percent, clean_numeric


# ============================================
# CORE KPIs (Scalar Values)
# ============================================

def calculate_processing_lead_time(df_entradas):
    df = df_entradas.copy()
    df['dt_llegada'] = clean_comparable_dates(df, 'FECHA DE LLEGADA')
    df['dt_proceso'] = clean_comparable_dates(df, 'FECHA EN PROCESO')
    valid = df.dropna(subset=['dt_llegada', 'dt_proceso'])
    if valid.empty: return 0, pd.DataFrame()
    valid['lead_time'] = (valid['dt_proceso'] - valid['dt_llegada']).dt.days
    return valid['lead_time'].mean(), valid

def calculate_72h_compliance(df_entradas):
    """
    Calculates 72h compliance.
    Priority 1: Use 'CUMPLIMIENTO 72 HORAS' column (User Request).
    Priority 2: Calculate from dates (Fallback).
    """
    df = df_entradas.copy()
    
    # Check for direct column (User's "Column AK")
    col_sla = next((c for c in df.columns if 'CUMPLIMIENTO' in c.upper() and '72' in c), None)
    
    if col_sla:
        # User logic: "CUMPLE" or "NO"
        # 1. Filter out empty/NaN rows first (don't count them)
        valid_sla = df[df[col_sla].notna() & (df[col_sla].astype(str).str.strip() != '')].copy()
        
        if valid_sla.empty:
            return 0.0, pd.DataFrame()  # Return empty df so downstream checks work
            
        def parse_sla(val):
            s = str(val).strip().upper()
            return 'CUMPLE' in s
            
        valid_sla['compliant'] = valid_sla[col_sla].apply(parse_sla)
        
        # Return percentage of VALID rows
        return valid_sla['compliant'].mean(), valid_sla
        
    # Fallback: Date Calculation
    df['dt_llegada'] = clean_comparable_dates(df, 'FECHA DE LLEGADA')
    df['dt_reporte'] = clean_comparable_dates(df, 'FECHA ENVIO DE REPORTE')
    valid = df.dropna(subset=['dt_llegada', 'dt_reporte'])
    if valid.empty: return 0.0, pd.DataFrame()
    valid['days_to_report'] = (valid['dt_reporte'] - valid['dt_llegada']).dt.days
    valid['compliant'] = valid['days_to_report'] <= 3
    return valid['compliant'].mean(), valid

def get_report_timeliness(df_entradas):
    """Inbound KPI #2: Reportes a Tiempo metrics."""
    _, valid = calculate_72h_compliance(df_entradas)
    if valid.empty:
        return {'pct': 0.0, 'on_time': 0, 'total': 0, 'avg_days': 0}
    
    # Using the same logic as 72h compliance but packaging for the new KPI card
    on_time = valid['compliant'].sum()
    total = len(valid)
    return {
        'pct': (on_time / total) * 100 if total > 0 else 0,
        'on_time': int(on_time),
        'total': int(total),
        'avg_days': valid['days_to_report'].mean()
    }


# ============================================
# CHART DATA - ENTRADAS
# ============================================

def get_lead_time_by_week(df_entradas):
    """Lead time trend using the 'SEMANA' column directly."""
    df = df_entradas.copy()
    if 'SEMANA' not in df.columns:
        return pd.DataFrame()
    
    df['dt_llegada'] = clean_comparable_dates(df, 'FECHA DE LLEGADA')
    df['dt_proceso'] = clean_comparable_dates(df, 'FECHA EN PROCESO')
    valid = df.dropna(subset=['dt_llegada', 'dt_proceso'])
    valid['lead_time'] = (valid['dt_proceso'] - valid['dt_llegada']).dt.days
    valid['SEMANA'] = clean_numeric(valid, 'SEMANA')
    
    # Filter out invalid weeks (0, empty, or negative)
    valid = valid[valid['SEMANA'] > 0]
    
    # Calculate total pieces
    valid['Piezas'] = clean_numeric(valid, 'PIEZAS CALZADO') + clean_numeric(valid, 'PIEZAS (ROPA, ACCESORIOS, ETC)')
    
    trend = valid.groupby('SEMANA').agg(
        Promedio=('lead_time', 'mean'),
        Pedimentos=('PEDIMENTO', 'count'),
        Total_Piezas=('Piezas', 'sum')
    ).reset_index()
    return trend

def get_volume_by_type(df_entradas):
    """Volume breakdown by TIPO DE MERCANCIA. Filters out 0 items."""
    df = df_entradas.copy()
    if 'TIPO DE MERCANCIA' not in df.columns:
        return pd.DataFrame()
    
    df['Piezas'] = clean_numeric(df, 'PIEZAS CALZADO') + clean_numeric(df, 'PIEZAS (ROPA, ACCESORIOS, ETC)')
    # Filter out 0 pieces
    df = df[df['Piezas'] > 0]
    
    grouped = df.groupby('TIPO DE MERCANCIA').agg(
        Total_Piezas=('Piezas', 'sum'),
        Pedimentos=('PEDIMENTO', 'count')
    ).reset_index()
    return grouped

def get_compliance_detail(df_entradas):
    """Detailed compliance breakdown for interactive chart."""
    _, valid = calculate_72h_compliance(df_entradas)
    if valid.empty:
        return pd.DataFrame()
    
    valid['Estado'] = valid['compliant'].map({True: 'Cumple', False: 'No Cumple'})
    summary = valid['Estado'].value_counts().reset_index()
    summary.columns = ['Estado', 'Cantidad']
    return summary

def get_arrivals_by_day(df_entradas):
    """Count arrivals by day of week using FECHA DE LLEGADA."""
    df = df_entradas.copy()
    df['dt_llegada'] = clean_comparable_dates(df, 'FECHA DE LLEGADA')
    valid = df.dropna(subset=['dt_llegada'])
    if valid.empty:
        return pd.DataFrame()
    
    valid['DiaSemana'] = valid['dt_llegada'].dt.day_name()
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    days_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    
    counts = valid['DiaSemana'].value_counts().reindex(days_order, fill_value=0).reset_index()
    counts.columns = ['DiaSemana', 'Llegadas']
    counts['DiaSemana'] = days_es  # Translate
    return counts


# ============================================
# NEW KPIs - INBOUND (ENTRADAS)
# ============================================

def get_cumplimiento_72h(df_entradas):
    """Cumplimiento 72 horas - % of reports sent within 72 hours."""
    rate, df = calculate_72h_compliance(df_entradas)
    if not df.empty and 'compliant' in df.columns:
        cumple = int(df['compliant'].sum())
        total = len(df)
    else:
        cumple = 0
        total = 0
    return {'pct': rate * 100, 'cumple': cumple, 'total': total}

def get_tiempo_ingreso(df_entradas):
    """Tiempo de ingreso - Average days from arrival to processing."""
    avg, df = calculate_processing_lead_time(df_entradas)
    min_val = df['lead_time'].min() if not df.empty else 0
    max_val = df['lead_time'].max() if not df.empty else 0
    return {'promedio': avg, 'min': min_val, 'max': max_val, 'total': len(df) if not df.empty else 0}

def get_volumen_recibido(df_entradas):
    """Volumen recibido - Total pieces and boxes received."""
    pzas_calzado = clean_numeric(df_entradas, 'PIEZAS CALZADO').sum()
    pzas_otros = clean_numeric(df_entradas, 'PIEZAS (ROPA, ACCESORIOS, ETC)').sum()
    cajas = clean_numeric(df_entradas, 'CAJAS').sum()
    tarimas = clean_numeric(df_entradas, 'TOTAL DE POSICIONES/TARIMAS').sum()
    pedimentos = len(df_entradas)
    return {
        'piezas': pzas_calzado + pzas_otros,
        'calzado': pzas_calzado,
        'otros': pzas_otros,
        'cajas': cajas,
        'tarimas': tarimas,
        'pedimentos': pedimentos
    }

def get_carga_operativa(df_entradas):
    """Carga operativa - Workload by responsible person."""
    if 'RESPONSABLE DE INGRESO' not in df_entradas.columns:
        return pd.DataFrame()
    df = df_entradas.copy()
    df['Piezas'] = clean_numeric(df, 'PIEZAS CALZADO') + clean_numeric(df, 'PIEZAS (ROPA, ACCESORIOS, ETC)')
    grouped = df.groupby('RESPONSABLE DE INGRESO').agg(
        Pedimentos=('PEDIMENTO', 'count'),
        Piezas=('Piezas', 'sum'),
        Cajas=('CAJAS', lambda x: clean_numeric(pd.DataFrame({'c': x}), 'c').sum())
    ).reset_index()
    grouped.columns = ['Responsable', 'Pedimentos', 'Piezas', 'Cajas']
    return grouped.sort_values('Pedimentos', ascending=False)

def get_tiempo_extra_indicador(df_entradas):
    """Tiempo extra - Operations that exceeded 72h threshold."""
    _, df = calculate_72h_compliance(df_entradas)
    if df.empty:
        return {'excedidos': 0, 'pct_excedido': 0, 'promedio_dias_extra': 0, 'total': 0}
        
    # If we have the days calculated, use them
    if 'days_to_report' in df.columns:
        excedidos = df[df['days_to_report'] > 3]
        avg_extra = (excedidos['days_to_report'] - 3).mean() if not excedidos.empty else 0
    else:
        # Fallback for text-based column: Just count non-compliant
        excedidos = df[~df['compliant']]
        avg_extra = 0 # Cannot calculate days from "NO CUMPLE" text
        
    return {
        'excedidos': len(excedidos),
        'pct_excedido': (len(excedidos) / len(df)) * 100 if len(df) > 0 else 0,
        'promedio_dias_extra': avg_extra,
        'total': len(df)
    }

def get_eficiencia_descarga(df_entradas):
    """Eficiencia descarga - Based on lead time performance."""
    avg, df = calculate_processing_lead_time(df_entradas)
    if df.empty:
        return {'eficiencia': 0, 'en_meta': 0, 'sobre_meta': 0}
    en_meta = len(df[df['lead_time'] <= 2])
    sobre_meta = len(df[df['lead_time'] > 2])
    eficiencia = (en_meta / len(df)) * 100 if len(df) > 0 else 0
    return {'eficiencia': eficiencia, 'en_meta': en_meta, 'sobre_meta': sobre_meta, 'total': len(df)}
