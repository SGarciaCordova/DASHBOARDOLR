import pandas as pd
import sys
import os

# Add src to path
sys.path.insert(0, os.getcwd())
from src import data_loader

try:
    print("Loading form data...")
    sheet_name = 'REPORTE MR 2026 RICARDO'
    client = data_loader.get_google_sheet_client()
    sh = client.open(sheet_name)
    
    with open('cols_dump.txt', 'w', encoding='utf-8') as f:
        # Check Sheet 1 (Entradas)
        ws1 = sh.get_worksheet(0)
        f.write(f'=== SHEET 0: TITLE="{ws1.title}" ===\n')
        headers1 = ws1.row_values(1)
        f.write(f"Headers Row 1: {headers1}\n")
        
        # Check Sheet 2 (Surtidos)
        if len(sh.worksheets()) > 1:
            ws2 = sh.get_worksheet(1)
            f.write(f'\n=== SHEET 1: TITLE="{ws2.title}" ===\n')
            headers2 = ws2.row_values(1)
            f.write(f"Headers Row 1: {headers2}\n")
            
    print("Done writing to cols_dump.txt")

except Exception as e:
    with open('cols_dump.txt', 'w') as f:
        f.write(f"Error: {e}")
    print(f"Error: {e}")
