
import sys
import os
import pandas as pd
from datetime import datetime, date, timedelta

# Add src to path
sys.path.append(os.path.abspath('.'))

from src import data_loader, kpi_engine

def debug():
    print("Loading data...")
    sheet_name = "REPORTE MR 2026 RICARDO"
    df_entradas, df_surtidos, is_mock = data_loader.load_data(sheet_name)
    
    print(f"Total Entradas: {len(df_entradas)}")
    print(f"Total Surtidos: {len(df_surtidos)}")
    
    if df_entradas.empty:
        print("Error: DataFrame is empty")
        return

    # Check date column
    date_col = 'FECHA DE LLEGADA'
    print(f"\nScanning column: {date_col}")
    print(f"Sample raw values: {df_entradas[date_col].head().tolist()}")
    
    # Run helper to see what it parses
    df_temp = df_entradas.copy()
    df_temp['_parsed'] = kpi_engine.clean_comparable_dates(df_temp, date_col)
    
    print(f"Parsed min date: {df_temp['_parsed'].min()}")
    print(f"Parsed max date: {df_temp['_parsed'].max()}")
    print(f"NaT count: {df_temp['_parsed'].isna().sum()}")
    
    # Simulate Dashboard Logic
    ref_date = date.today()
    # If today is 2026-02-10 (from prompt)
    # kpi_engine.get_previous_period_data uses datetime.now() if passed date? 
    # No, I updated it to accept ref_date.
    
    print(f"\nReference Date: {ref_date}")
    
    # Call get_previous_period_data
    df_prev = kpi_engine.get_previous_period_data(df_entradas, date_col, period='week', ref_date=ref_date)
    
    print(f"\nPrevious Period Data (Week):")
    print(f"Row count: {len(df_prev)}")
    if not df_prev.empty:
        # Re-calc dates to show range
        dates = kpi_engine.clean_comparable_dates(df_prev, date_col)
        print(f"Range in Prev DF: {dates.min()} to {dates.max()}")
    else:
        print("EMPTY DATAFRAME!")
        
    # Calculate SLA
    current_sla, _ = kpi_engine.calculate_72h_compliance(df_entradas)
    prev_sla, _ = kpi_engine.calculate_72h_compliance(df_prev)
    
    print(f"\nCurrent SLA (All Time/Filtered?): {current_sla*100:.1f}%")
    print(f"Previous SLA: {prev_sla*100:.1f}%")
    
    wow = kpi_engine.calculate_wow_change(current_sla*100, prev_sla*100)
    print(f"WoW Change: {wow:.1f}%")
    
    # Check if calculation logic returns 100 if prev is 0
    if prev_sla == 0:
        print("CONFIRMED: Previous SLA is 0. This causes 100% change.")

if __name__ == "__main__":
    debug()
