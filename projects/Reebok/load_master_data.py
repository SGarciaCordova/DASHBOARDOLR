import os
import sqlite3
import pandas as pd
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

DB_PATH = r"c:\Users\Usuario1\Desktop\Antigravity SGC\data\wms_data.db"
CSV_PATH = r"C:\Users\Usuario1\Downloads\MASTER DATA REEBOK.csv"

def find_col(df, candidates: list):
    for name in candidates:
        matches = [c for c in df.columns if name in c]
        if matches:
            return matches[0]
    return None

def main():
    if not os.path.exists(CSV_PATH):
        log.error(f"Archivo no encontrado: {CSV_PATH}")
        sys.exit(1)
        
    log.info(f"Cargando el archivo histórico {CSV_PATH} en {DB_PATH} (tabla: entradas)...")
    try:
        # Tratamos de leerlo (en caso de que sea csv delimitado por comas)
        df = pd.read_csv(CSV_PATH, encoding="latin-1", on_bad_lines="skip", dtype=str)
        # Limpiar columnas
        df.columns = [
            str(c).strip().lower().replace(" ", "_").replace(":", "").replace(".", "")
            for c in df.columns
        ]

        # Validamos columnas encontradas
        log.info(f"Columnas detectadas: {df.columns.values}")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Limpiamos la tabla primero para partir de una base super limpia
        log.info("Vaciando tabla entradas de SQLite para el llenado histórico...")
        conn.execute("DELETE FROM entradas")
        conn.commit()

        count = 0
        for _, row in df.iterrows():
            docto_id = row.get(find_col(df, ["documento_id", "docto_id", "pedido", "documento", "docto", "doc"]), "")
            
            # Filtramos INVE- (inventarios)
            if str(docto_id).upper().startswith("INVE-"):
                continue

            referencia  = row.get(find_col(df, ["referencia", "ref", "caja"]), "")
            fecha       = row.get(find_col(df, ["fecha", "fecha_creacion", "f_alta", "date", "creac"]), "")
            sku         = row.get(find_col(df, ["skuright", "sku", "articulo", "item", "codigo"]), "")
            descripcion = row.get(find_col(df, ["desc", "descripcion", "description", "nombre"]), "")
            cantidad    = row.get(find_col(df, ["cantidad_recibida", "cantidad", "piezas", "recibida", "cant_recibida", "qty"]), 0)
            tarimas     = row.get(find_col(df, ["tarimas", "pallets", "huella", "tarima"]), 0)
            calidad     = row.get(find_col(df, ["calidad", "quality", "condicion", "estado_calidad"]), "")

            try:
                cantidad = float(str(cantidad).replace(",", "").replace('"', "").strip())
            except Exception:
                cantidad = 0
            try:
                tarimas = float(str(tarimas).replace(",", "").replace('"', "").strip())
            except Exception:
                tarimas = 0

            cursor.execute("""
                INSERT OR REPLACE INTO entradas
                  (docto_id, referencia, fecha, sku, descripcion, cantidad, tarimas, calidad)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(docto_id), str(referencia), str(fecha), str(sku),
                  str(descripcion), cantidad, tarimas, str(calidad)))
            count += 1

        conn.commit()
        conn.close()
        log.info(f"✅ ¡Datos históricos maestros cargados correctamente! Total de filas reales insertadas (ignorando inventarios): {count}.")

    except Exception as e:
        log.error(f"Error procesando CSV histórico: {e}")

if __name__ == "__main__":
    main()
