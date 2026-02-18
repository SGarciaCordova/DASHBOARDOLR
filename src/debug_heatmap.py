import pandas as pd
import sys
import os

# Suppress streamlit warnings
os.environ['STREAMLIT_hIDE_WARNINGS'] = '1'

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

import ubicaciones_loader

with open("debug_heatmap_output.txt", "w", encoding="utf-8") as f:
    f.write("--- START DEBUG ---\n")
    try:
        f.write("Loading locations...\n")
        df_locations = ubicaciones_loader.load_locations()
        f.write(f"Locations loaded: {len(df_locations)} rows\n")
        if not df_locations.empty:
            f.write(f"Columns: {df_locations.columns.tolist()}\n")
            f.write(f"Max POSICION: {df_locations['POSICION'].max()}\n")
    except Exception as e:
        f.write(f"Error loading locations: {e}\n")

    try:
        f.write("\nLoading Inventory...\n")
        df_inv = ubicaciones_loader.load_all_inventory()
        f.write(f"Inventory loaded: {len(df_inv)} rows\n")
    except Exception as e:
        f.write(f"Error loading inventory: {e}\n")

    try:
        f.write("\nComputing Heatmap Data...\n")
        heatmap_data = ubicaciones_loader.get_heatmap_data(df_inv, df_locations)
        f.write(f"Keys: {list(heatmap_data.keys())}\n")
        f.write(f"Pasillos count: {len(heatmap_data.get('pasillos', []))}\n")
        f.write(f"Max Position: {heatmap_data.get('max_position')}\n")
        f.write(f"Cells count: {len(heatmap_data.get('cells', []))}\n")
        
        if len(heatmap_data.get("cells", [])) > 0:
            f.write(f"Sample Cell: {heatmap_data['cells'][0]}\n")
            
            # Check cell density
            non_zero = [c for c in heatmap_data['cells'] if c['qty'] > 0]
            f.write(f"Cells with >0 qty: {len(non_zero)}\n")
            
    except Exception as e:
        f.write(f"Error computing heatmap: {e}\n")
    f.write("--- END DEBUG ---\n")
