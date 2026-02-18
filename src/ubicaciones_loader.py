"""
ubicaciones_loader.py — Data loader for the Dashboard de Ubicaciones.

Loads:
  - Client master from Google Sheets
  - Location master from Google Sheets
  - Inventory CSVs (ON, Reebok, Piarena) from data/inventarios/
  
Computes KPIs and chart data for the dashboard.
"""
import pandas as pd
import os
import streamlit as st

# ── Google Sheets URLs ──────────────────────────────────────────────────────
SHEET_ID = "1Dxg9ANs_sgQu0oU40F2bIMY9Icd7Wpt87sxA-HWA1_M"
CLIENTS_URL  = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
LOCATIONS_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1305145196"

# ── Inventory CSV paths ────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "inventarios")

# Client → CSV mapping  (client_label: filename)
CLIENT_INVENTORY_MAP = {
    "ON": "on_inventory.csv",
    "REEBOK": "reebok_inventory.csv",
    "PIARENA": "piarena_inventory.csv",
}

# ON is a grouping of Monte Rosa (211) + Regency (212)
ON_CLIENT_IDS = [211, 212]
REEBOK_CLIENT_ID = 208


# ═══════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=600, show_spinner="Cargando maestro de clientes…")
def load_clients():
    """Load client master from Google Sheets."""
    try:
        df = pd.read_csv(CLIENTS_URL)
        df.columns = df.columns.str.strip()
        df["ID CLIENTE"] = pd.to_numeric(df["ID CLIENTE"], errors="coerce").astype("Int64")
        df["CLIENTES"] = df["CLIENTES"].astype(str).str.strip()
        return df
    except Exception as e:
        print(f"[ubicaciones_loader] Error loading clients: {e}")
        return pd.DataFrame(columns=["ID CLIENTE", "CLIENTES"])


@st.cache_data(ttl=600, show_spinner="Cargando maestro de ubicaciones…")
def load_locations():
    """Load location master from Google Sheets."""
    try:
        df = pd.read_csv(LOCATIONS_URL)
        df.columns = df.columns.str.strip()
        df["ID UBICACION"] = pd.to_numeric(df["ID UBICACION"], errors="coerce").astype("Int64")
        df["PASILLO"] = df["PASILLO"].astype(str).str.strip()
        df["UBICACION"] = df["UBICACION"].astype(str).str.strip()

        # Parse UBICACION (format: PASILLO-POSICIÓN-NIVEL) into components
        parts = df["UBICACION"].str.split("-", expand=True)
        if parts.shape[1] >= 3:
            df["POSICION"] = pd.to_numeric(parts[1], errors="coerce").astype("Int64")
            df["NIVEL"] = pd.to_numeric(parts[2], errors="coerce").astype("Int64")
        else:
            df["POSICION"] = pd.NA
            df["NIVEL"] = pd.NA

        return df
    except Exception as e:
        print(f"[ubicaciones_loader] Error loading locations: {e}")
        return pd.DataFrame(columns=["PASILLO", "ID UBICACION", "UBICACION", "POSICION", "NIVEL"])


@st.cache_data(ttl=600, show_spinner="Cargando inventario…")
def load_inventory(client_key: str):
    """Load inventory CSV for a specific client."""
    filename = CLIENT_INVENTORY_MAP.get(client_key)
    if not filename:
        return pd.DataFrame()

    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"[ubicaciones_loader] File not found: {filepath}")
        return pd.DataFrame()

    try:
        df = pd.read_csv(filepath, low_memory=False)
        df.columns = df.columns.str.strip()
        df["ubicacion_id"] = pd.to_numeric(df["ubicacion_id"], errors="coerce").astype("Int64")
        df["inventario_cantidad"] = pd.to_numeric(df["inventario_cantidad"], errors="coerce").fillna(0)
        return df
    except Exception as e:
        print(f"[ubicaciones_loader] Error loading inventory for {client_key}: {e}")
        return pd.DataFrame()


def load_all_inventory():
    """Load and concatenate all inventory CSVs, tagged with client label."""
    frames = []
    for client_key, filename in CLIENT_INVENTORY_MAP.items():
        df = load_inventory(client_key)
        if not df.empty:
            df["_client"] = client_key
            frames.append(df)
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def excel_col_to_int(col_str):
    """Converts Excel-style column name (A, Z, AA) to integer (1, 26, 27)."""
    if not isinstance(col_str, str):
        return 0
    num = 0
    for c in col_str.upper():
        if 'A' <= c <= 'Z':
            num = num * 26 + (ord(c) - ord('A') + 1)
    return num

# ═══════════════════════════════════════════════════════════════════════════
#  KPI CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════════

def compute_kpis(df_inv: pd.DataFrame, df_locations: pd.DataFrame):
    """
    Compute dashboard KPIs for a given inventory dataframe.
    Returns dict with all KPI values.
    """
    total_locations = len(df_locations)

    if df_inv.empty:
        return {
            "total_locations": total_locations,
            "occupied_locations": 0,
            "occupancy_pct": 0.0,
            "total_skus": 0,
            "total_piezas": 0,
            "pasillos_used": 0,
            "has_data": False,
        }

    # Join inventory with locations to get PASILLO info
    df_merged = df_inv.merge(
        df_locations[["ID UBICACION", "PASILLO", "UBICACION", "POSICION", "NIVEL"]],
        left_on="ubicacion_id",
        right_on="ID UBICACION",
        how="left",
    )

    occupied_ids = df_merged["ubicacion_id"].dropna().nunique()
    total_skus = df_merged["producto_sku"].dropna().nunique()
    total_piezas = df_merged["inventario_cantidad"].sum()
    pasillos_used = df_merged["PASILLO"].dropna().nunique()
    occupancy_pct = (occupied_ids / total_locations * 100) if total_locations > 0 else 0

    return {
        "total_locations": total_locations,
        "occupied_locations": int(occupied_ids),
        "occupancy_pct": round(occupancy_pct, 1),
        "total_skus": int(total_skus),
        "total_piezas": int(total_piezas),
        "pasillos_used": int(pasillos_used),
        "has_data": True,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  CHART DATA
# ═══════════════════════════════════════════════════════════════════════════

def get_occupancy_by_pasillo(df_inv: pd.DataFrame, df_locations: pd.DataFrame):
    """Bar chart: % occupied locations per pasillo."""
    if df_inv.empty:
        return []

    # Total locations per pasillo
    total_per_pasillo = df_locations.groupby("PASILLO")["ID UBICACION"].nunique().reset_index()
    total_per_pasillo.columns = ["PASILLO", "total"]

    # Occupied locations per pasillo
    df_merged = df_inv.merge(
        df_locations[["ID UBICACION", "PASILLO"]],
        left_on="ubicacion_id",
        right_on="ID UBICACION",
        how="left",
    )
    occupied_per_pasillo = df_merged.groupby("PASILLO")["ubicacion_id"].nunique().reset_index()
    occupied_per_pasillo.columns = ["PASILLO", "occupied"]

    # Merge
    result = total_per_pasillo.merge(occupied_per_pasillo, on="PASILLO", how="left").fillna(0)
    result["pct"] = (result["occupied"] / result["total"] * 100).round(1)
    
    # Sort using Excel logic
    result["sort_key"] = result["PASILLO"].apply(excel_col_to_int)
    result = result.sort_values("sort_key").drop(columns=["sort_key"])

    return result.to_dict("records")


def get_top_skus(df_inv: pd.DataFrame, top_n=10):
    """Bar chart: top N SKUs by quantity."""
    if df_inv.empty:
        return []

    grouped = (
        df_inv.groupby(["producto_sku", "producto_desc"])["inventario_cantidad"]
        .sum()
        .reset_index()
        .sort_values("inventario_cantidad", ascending=False)
        .head(top_n)
    )
    grouped.columns = ["sku", "desc", "cantidad"]
    # Truncate descriptions for display
    grouped["label"] = grouped["desc"].astype(str).str[:30]
    return grouped.to_dict("records")


def get_distribution_by_level(df_inv: pd.DataFrame, df_locations: pd.DataFrame):
    """Doughnut chart: pieces by storage level (1-6)."""
    if df_inv.empty:
        return []

    df_merged = df_inv.merge(
        df_locations[["ID UBICACION", "NIVEL"]],
        left_on="ubicacion_id",
        right_on="ID UBICACION",
        how="left",
    )
    grouped = df_merged.groupby("NIVEL")["inventario_cantidad"].sum().reset_index()
    grouped.columns = ["nivel", "cantidad"]
    grouped = grouped.dropna(subset=["nivel"])
    grouped["nivel"] = grouped["nivel"].astype(int)
    grouped = grouped.sort_values("nivel")
    grouped["label"] = "Nivel " + grouped["nivel"].astype(str)
    return grouped.to_dict("records")


def get_heatmap_data(df_inv: pd.DataFrame, df_locations: pd.DataFrame):
    """
    Grid heatmap data: pasillo × position, summing quantities.
    Returns: { pasillos: [...], max_position: N, cells: [{pasillo, position, qty, locations: [...]}] }
    """
    if df_inv.empty:
        return {"pasillos": [], "max_position": 0, "cells": []}

    df_merged = df_inv.merge(
        df_locations[["ID UBICACION", "PASILLO", "POSICION", "NIVEL", "UBICACION"]],
        left_on="ubicacion_id",
        right_on="ID UBICACION",
        how="left",
    )

    # Aggregate by pasillo + position + nivel
    grouped = (
        df_merged.groupby(["PASILLO", "POSICION", "NIVEL"])
        .agg(qty=("inventario_cantidad", "sum"))
        .reset_index()
    )
    
    # Second aggregation to group levels into the cell
    cells_dict = {}
    for _, row in grouped.iterrows():
        key = (str(row["PASILLO"]), int(row["POSICION"]))
        if key not in cells_dict:
            cells_dict[key] = {"pasillo": key[0], "position": key[1], "qty": 0, "levels": {}}
        
        lvl = int(row["NIVEL"]) if pd.notna(row["NIVEL"]) else 0
        qty = int(row["qty"])
        cells_dict[key]["qty"] += qty
        cells_dict[key]["levels"][lvl] = qty

    pasillos = sorted(df_locations["PASILLO"].dropna().unique(), key=excel_col_to_int)
    max_position = int(df_locations["POSICION"].dropna().max()) if not df_locations["POSICION"].dropna().empty else 0

    cells = list(cells_dict.values())

    return {
        "pasillos": pasillos,
        "max_position": max_position,
        "cells": cells,
    }


def get_client_list(df_clients: pd.DataFrame):
    """
    Build enriched client list with inventory status.
    Returns list of dicts for the client table.
    """
    clients = []
    for _, row in df_clients.iterrows():
        cid = row["ID CLIENTE"]
        name = str(row["CLIENTES"])

        # Determine if this client has inventory data
        has_data = False
        client_key = None
        
        # Check by ID or Name
        if cid == REEBOK_CLIENT_ID:
            has_data = True
            client_key = "REEBOK"
        elif cid in ON_CLIENT_IDS:
            has_data = True
            client_key = "ON"
        elif "PIARENA" in name.upper():
            has_data = True
            client_key = "PIARENA"

        clients.append({
            "id": int(cid) if pd.notna(cid) else 0,
            "name": name,
            "has_data": has_data,
            "client_key": client_key,
        })

    # Group ON clients (Monte Rosa + Regency) into single entry
    on_ids = [c for c in clients if c["client_key"] == "ON"]
    others = [c for c in clients if c["client_key"] != "ON"]

    if on_ids:
        on_entry = {
            "id": ON_CLIENT_IDS[0],
            "name": "ON (Monte Rosa + Regency)",
            "has_data": True,
            "client_key": "ON",
        }
        others.insert(0, on_entry)  # Put ON at top

    # Prioritize certain clients in the list display order
    priority_order = ["ON", "REEBOK", "PIARENA"]
    
    final = []
    # Add prioritized clients first
    for key in priority_order:
        matches = [c for c in others if c["client_key"] == key]
        final.extend(matches)
        others = [c for c in others if c["client_key"] != key]
    
    # Add the rest
    final.extend(others)

    return final
