import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import random
from datetime import datetime, timedelta
import numpy as np
import streamlit as st

def clean_date_series(series):
    """
    Robust date parser that handles multiple formats and errors.
    Returns pd.NaT for invalid dates.
    """
    # First, try standard pandas parsing
    # dayfirst=True is common in LATAM (DD/MM/YYYY)
    return pd.to_datetime(series, dayfirst=True, errors='coerce')

def get_google_sheet_client(credentials_path='credentials.json'):
    if not os.path.exists(credentials_path):
        return None
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(creds)
    return client

def deduplicate_headers(headers):
    """
    Renames duplicate headers by appending .1, .2, etc.
    e.g. ['%', 'Qt', '%'] -> ['%', 'Qt', '%.1']
    """
    counts = {}
    new_headers = []
    for h in headers:
        h = str(h).strip()  # Clean spaces from Excel headers!
        if h in counts:
            counts[h] += 1
            new_headers.append(f"{h}.{counts[h]}")
        else:
            counts[h] = 0
            new_headers.append(h)
    return new_headers

def generate_mock_data():
    """Generates mock data with deduplicated headers structure."""
    
    # --- Mock Entradas ---
    entradas_data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(50):
        llegada = base_date + timedelta(days=random.randint(0, 25))
        en_proceso = llegada + timedelta(days=random.randint(1, 4)) if random.random() > 0.1 else pd.NaT
        reporte = llegada + timedelta(days=random.randint(2, 6))
        
        entradas_data.append({
            "PEDIMENTO": f"PED-{1000+i}",
            "FECHA DE LLEGADA": llegada,
            "FECHA EN PROCESO": en_proceso,
            "FECHA ENVIO DE REPORTE": reporte,
            "CUMPLIMIENTO 72 HORAS": "CUMPLE" if (reporte - llegada).days <= 3 else "NO CUMPLE"
        })
    df_entradas = pd.DataFrame(entradas_data)

    # --- Mock Surtidos ---
    # We construct this data row by row as a list of dicts with DISTINCT keys first
    # referencing the specific positions of '%' columns in the user's schema:
    # ... PIEZAS SURTIDAS, %, PIEZAS ETIQUETADAS / SENSOR, %, DISTRIBUCION, %, ...
    
    surtidos_rows = []
    for i in range(50):
        fecha_req = base_date + timedelta(days=random.randint(0, 30))
        fecha_ent = fecha_req + timedelta(days=random.randint(-1, 3)) if random.random() > 0.1 else pd.NaT
        total = random.randint(100, 500)
        surtidas = int(total * random.uniform(0.8, 1.0))
        
        # We use the DEDUPLICATED names that our loader would produce
        row = {
            "FECHA": fecha_req,
            "CLIENTE": random.choice(["Cliente A", "Cliente B"]),
            "TOTAL DE PIEZAS": total,
            "PIEZAS SURTIDAS": surtidas,
            "%": surtidas/total,               # 1st % (Surtido)
            "PIEZAS ETIQUETADAS / SENSOR": surtidas,
            "%.1": random.uniform(0.7, 0.9),  # 2nd % (Etiquetado)
            "DISTRIBUCION": "En Ruta",
            "%.2": random.uniform(0.5, 0.8),  # 3rd % (Distribucion)
            "AUDITORIA": "Pendiente",
            "%.3": random.uniform(0.4, 1.0),  # 4th % (Auditoria)
            "FECHA A ENTREGAR": fecha_req + timedelta(days=2),
            "FECHA ENTREGADO": fecha_ent
        }
        surtidos_rows.append(row)

    df_surtidos = pd.DataFrame(surtidos_rows)
    return df_entradas, df_surtidos

@st.cache_data(ttl=600, show_spinner=False)
def load_data(sheet_name=None, credentials_path='credentials.json'):
    client = get_google_sheet_client(credentials_path)
    
    if client and sheet_name:
        try:
            sheet = client.open(sheet_name)
            
            # Helper to load and deduplicate
            def read_sheet_to_df(ws_name):
                ws = sheet.worksheet(ws_name)
                rows = ws.get_all_values()
                if not rows:
                    return pd.DataFrame()
                
                headers = rows[0]
                unique_headers = deduplicate_headers([h.strip() for h in headers])
                data = rows[1:]
                
                return pd.DataFrame(data, columns=unique_headers)

            df_entradas = read_sheet_to_df("ENTRADAS")
            df_surtidos = read_sheet_to_df("SURTIDOS")

            # --- FILTER EMPTY ROWS (Fix for phantom backlog) ---
            # Remove rows where key identifier columns are empty/blank strings
            if 'PEDIMENTO' in df_entradas.columns:
                df_entradas = df_entradas[df_entradas['PEDIMENTO'].astype(str).str.strip() != '']
            
            if 'CLIENTE' in df_surtidos.columns:
                df_surtidos = df_surtidos[df_surtidos['CLIENTE'].astype(str).str.strip() != '']

            # --- ROBUST DATE CLEANING ---
            date_cols_entradas = ['FECHA DE LLEGADA', 'FECHA EN PROCESO', 'FECHA ENVIO DE REPORTE']
            date_cols_surtidos = ['FECHA', 'FECHA A ENTREGAR', 'FECHA ENTREGADO', 'FECHA / HORA ENTREGADO', 'FECHA/HORA ENTREGADO']

            for col in date_cols_entradas:
                if col in df_entradas.columns:
                    df_entradas[col] = clean_date_series(df_entradas[col])
            
            for col in date_cols_surtidos:
                if col in df_surtidos.columns:
                    df_surtidos[col] = clean_date_series(df_surtidos[col])

            # --- NUMERIC CLEANING ---
            if 'TOTAL DE PIEZAS' in df_surtidos.columns:
                 df_surtidos['TOTAL DE PIEZAS'] = pd.to_numeric(df_surtidos['TOTAL DE PIEZAS'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

            return df_entradas, df_surtidos, False
        except Exception as e:
            print(f"Error loading from Google Sheets: {e}")
            return *generate_mock_data(), True
    else:
        print("No credentials or sheet name provided. Using Mock Data.")
        return *generate_mock_data(), True
