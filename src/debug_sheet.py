from src import data_loader
import pandas as pd

def debug_sheet_structure(sheet_name="REPORTE MR 2026 RICARDO"):
    client = data_loader.get_google_sheet_client()
    if not client:
        print("Failed to connect.")
        return

    try:
        sheet = client.open(sheet_name)
        print(f"✅ Opened Spreadsheet: '{sheet_name}'")
        
        # List ALL worksheets
        worksheets = sheet.worksheets()
        print(f"\n📑 Found {len(worksheets)} worksheets:")
        for ws in worksheets:
            print(f" - '{ws.title}' (ID: {ws.id})")
            
        print("\n--- Inspecting Target Sheets ---")
        for ws_name in ["ENTRADAS", "SURTIDOS"]:
            print(f"\n🔎 Checking '{ws_name}'...")
            try:
                ws = sheet.worksheet(ws_name)
                rows = ws.get_all_values()
                count = len(rows)
                print(f"   -> Total Rows: {count}")
                if count > 0:
                    print(f"   -> Header (Row 1): {rows[0]}")
                    print(f"   -> Date Sample (Row 2, Col 1-5): {rows[1][:5] if count > 1 else 'N/A'}")
            except Exception as e:
                print(f"   ❌ Error: Could not find or read '{ws_name}': {e}")
                # Try to find close matches
                for ws in worksheets:
                    if ws_name.lower() in ws.title.lower():
                        print(f"      (Did you mean '{ws.title}'?)")

    except Exception as e:
        print(f"❌ Error opening spreadsheet: {e}")

if __name__ == "__main__":
    import sys
    # Redirect stdout to a file to capture output reliably
    with open('debug_output.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        debug_sheet_structure()
    sys.stdout = sys.__stdout__
    print("Debug completed. Check debug_output.txt")
