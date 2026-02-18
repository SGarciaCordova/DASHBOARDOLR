"""
comparativas.py — Filtros de fecha, comparaciones WoW y tendencias.
Funciones para filtrar datos por período y calcular cambios semana a semana.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.kpis.helpers import clean_comparable_dates

def filter_by_date_range(df, date_col, period='all'):
    """
    Filters dataframe by date range.
    Periods: 'today', 'week', 'month', 'all'
    """
    if df.empty or date_col not in df.columns:
        return df
    
    df = df.copy()
    df['_filter_date'] = clean_comparable_dates(df, date_col)
    
    if period == 'all':
        return df.drop(columns=['_filter_date'], errors='ignore')
    
    from datetime import datetime, timedelta
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if period == 'today':
        start = today
        end = today + timedelta(days=1)
    elif period == 'week':
        start = today - timedelta(days=today.weekday())  # Monday
        end = start + timedelta(days=7)
    elif period == 'month':
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year+1, month=1, day=1)
        else:
            end = today.replace(month=today.month+1, day=1)
    else:
        return df.drop(columns=['_filter_date'], errors='ignore')
    
    filtered = df[(df['_filter_date'] >= start) & (df['_filter_date'] < end)]
    return filtered.drop(columns=['_filter_date'], errors='ignore')

def filter_by_custom_dates(df, date_col, start_date, end_date):
    """
    Filters dataframe by custom date range from calendar picker.
    start_date and end_date should be datetime.date objects.
    """
    if df.empty or date_col not in df.columns:
        return df
    
    df = df.copy()
    df['_filter_date'] = clean_comparable_dates(df, date_col)
    
    from datetime import datetime
    # Convert date to datetime for comparison
    start = datetime.combine(start_date, datetime.min.time())
    end = datetime.combine(end_date, datetime.max.time())
    
    filtered = df[(df['_filter_date'] >= start) & (df['_filter_date'] <= end)]
    return filtered.drop(columns=['_filter_date'], errors='ignore')

def get_previous_period_data(df, date_col, period='week', ref_date=None):
    """Gets data from the previous period for WoW comparison."""
    if df.empty or date_col not in df.columns:
        return df.iloc[0:0]  # Empty with same schema
    
    df = df.copy()
    df['_filter_date'] = clean_comparable_dates(df, date_col)
    
    from datetime import datetime, timedelta
    
    # Defaults to today if ref_date not provided
    if ref_date is None:
        ref = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif isinstance(ref_date, datetime):
        ref = ref_date
    else:
        # Convert date to datetime
        ref = datetime.combine(ref_date, datetime.min.time())
    
    if period == 'week':
        # Previous week relative to ref
        # If ref is today (Tuesday), prev week is Last Monday -> Last Sunday?
        # Standard: 7 days window back from ref
        start = ref - timedelta(days=7)
        end = ref
        
    elif period == 'month':
        # Previous month relative to ref
        # If ref is Feb 1st, prev month is Jan 1st - Feb 1st
        if ref.month == 1:
            start = ref.replace(year=ref.year-1, month=12, day=1)
        else:
            start = ref.replace(month=ref.month-1, day=1)
        # End is the reference date (start of current period)
        end = ref.replace(day=1)
        
    else:
        return df.iloc[0:0]
    
    filtered = df[(df['_filter_date'] >= start) & (df['_filter_date'] < end)]
    return filtered.drop(columns=['_filter_date'], errors='ignore')

def calculate_wow_change(current, previous):
    """Calculates absolute percentage point change (Current - Previous)."""
    # For rate metrics (%), we want the absolute difference (pp), not relative growth
    # e.g., 80% -> 90% should be +10%, not +12.5%
    return current - previous
