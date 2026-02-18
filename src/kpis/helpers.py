"""
helpers.py — Utilidades de sanitización y limpieza de datos.
Funciones genéricas usadas por todos los demás módulos de KPI.
"""
import pandas as pd
import numpy as np
from datetime import datetime

def clean_comparable_dates(df, col_name):
    """Parses mixed date formats to datetime objects."""
    if col_name not in df.columns:
        return pd.Series(pd.NaT, index=df.index)
    return pd.to_datetime(df[col_name], dayfirst=False, errors='coerce')

def clean_numeric_percent(df, col_name):
    """Parses '100%' style strings to 0.0-1.0 floats. Blanks remain NaN."""
    if col_name not in df.columns:
        return pd.Series(np.nan, index=df.index)
    # Check for empty strings/blanks first
    raw = df[col_name].astype(str).str.strip()
    s = raw.str.replace('%', '', regex=False)
    # Replace empty strings with NaN
    s = s.replace('', np.nan)
    vals = pd.to_numeric(s, errors='coerce')
    
    # If values are like 75.00, it's 75, not 0.75. 
    # Logic: if the average of non-NaN values is high, divide by 100.
    non_nan = vals.dropna()
    if not non_nan.empty and non_nan.mean() > 2.0:
        vals = vals / 100.0
    return vals

def clean_numeric(df, col_name):
    """Safely converts column to numeric. Blanks become 0 for safe summation."""
    if col_name not in df.columns:
        return pd.Series(0, index=df.index)
    raw = df[col_name].astype(str).str.strip().replace('', np.nan)
    return pd.to_numeric(raw, errors='coerce').fillna(0)
