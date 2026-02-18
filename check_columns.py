import pandas as pd
from src import data_loader

try:
    sheet_name = "REPORTE MR 2026 RICARDO"
    print(f"Loading data from: {sheet_name}")
    df_entradas_raw, df_surtidos_raw, is_mock = data_loader.load_data(sheet_name)
    
    if is_mock:
        print("WARNING: Loaded MOCK data. Credentials might be missing or invalid.")
    else:
        print("SUCCESS: Loaded REAL data.")

    print("\n--- SURTIDOS COLUMNS ---")
    print(df_surtidos_raw.columns.tolist())
    
    # Check for date columns samples
    print("\n--- DATE SAMPLES ---")
    for col in df_surtidos_raw.columns:
        if 'FECHA' in col.upper() or 'FINAL' in col.upper() or 'ENTREGADO' in col.upper():
            print(f"\nSample {col}:")
            print(df_surtidos_raw[col].dropna().head(3))
            
except Exception as e:
    print(f"ERROR: {e}")
