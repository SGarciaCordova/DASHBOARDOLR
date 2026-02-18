from src import data_loader
from src import database
import pandas as pd

def sync_sheets_to_db(sheet_name="REPORTE MR 2026 RICARDO"):
    """
    Fetches data from Google Sheets and saves it to local SQLite DB.
    Returns: (success, message)
    """
    try:
        # 1. Fetch from Sheets using existing loader (this does the cleaning too!)
        # We need to bypass the cache to get fresh data, so we might need a dedicated fetcher
        # or just rely on data_loader.load_data. 
        # Since data_loader.load_data is cached via Streamlit, we should use the internal helper 
        # or ensure we can force refresh.
        # Ideally, we should refactor data_loader to separate 'fetching' from 'streamlit caching'.
        
        # For now, we will re-instantiate the client locally to avoid Streamlit cache issues in a script context
        # But since we are likely calling this FROM Streamlit, we can just call the logic.
        
        # We will use the internal logic from data_loader manually to ensure a fresh fetch
        client = data_loader.get_google_sheet_client()
        if not client:
            return False, "No se pudo conectar a Google Sheets (Error de Credenciales)."
            
        sheet = client.open(sheet_name)
        
        # Helper from data_loader reused
        def read_sheet(ws_name):
            ws = sheet.worksheet(ws_name)
            rows = ws.get_all_values()
            if not rows: return pd.DataFrame()
            headers = data_loader.deduplicate_headers(rows[0])
            return pd.DataFrame(rows[1:], columns=headers)

        df_entradas = read_sheet("ENTRADAS")
        df_surtidos = read_sheet("SURTIDOS")
        
        # Apply Cleaners
        date_cols_entradas = ['FECHA DE LLEGADA', 'FECHA EN PROCESO', 'FECHA ENVIO DE REPORTE']
        date_cols_surtidos = ['FECHA', 'FECHA A ENTREGAR', 'FECHA ENTREGADO']

        # 1. Start by stripping empty rows based on critical columns
        if 'FECHA DE LLEGADA' in df_entradas.columns:
            df_entradas = df_entradas[df_entradas['FECHA DE LLEGADA'].astype(str).str.strip() != '']
            
        if 'FECHA' in df_surtidos.columns:
            df_surtidos = df_surtidos[df_surtidos['FECHA'].astype(str).str.strip() != '']

        for col in date_cols_entradas:
            if col in df_entradas.columns:
                df_entradas[col] = data_loader.clean_date_series(df_entradas[col])
                # Convert NaT to None/String for SQLite compatibility if needed, 
                # but pandas to_sql handles datetime objects reasonably well.
        
        for col in date_cols_surtidos:
            if col in df_surtidos.columns:
                df_surtidos[col] = data_loader.clean_date_series(df_surtidos[col])

        # Numeric cleaning
        if 'TOTAL DE PIEZAS' in df_surtidos.columns:
             df_surtidos['TOTAL DE PIEZAS'] = pd.to_numeric(df_surtidos['TOTAL DE PIEZAS'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

        # 2. Save to DB
        database.init_db()
        database.save_dataframe_to_db(df_entradas, 'entradas')
        database.save_dataframe_to_db(df_surtidos, 'surtidos')
        
        return True, f"Sincronización Exitosa. Entradas: {len(df_entradas)}, Surtidos: {len(df_surtidos)}"
        
    except Exception as e:
        return False, f"Error durante la sincronización: {str(e)}"

if __name__ == "__main__":
    success, msg = sync_sheets_to_db()
    print(msg)
