import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

sql_drop = "DROP VIEW IF EXISTS wms_aeropuerto;"
sql_create = """
CREATE VIEW wms_aeropuerto AS 
SELECT 
    docto_id, 
    referencia, 
    fecha, 
    (CASE WHEN (fecha ~ '^\d{4}-\d{2}-\d{2}'::text) THEN (fecha)::timestamp 
          ELSE NULL::timestamp without time zone 
     END)::time without time zone AS hora,
    cliente, 
    cantidad_pedida, 
    cantidad_surtida, 
    tarimas, 
    tasa_de_cumplimiento, 
    estado,
    fecha_entrega
FROM wms_aeropuerto_raw 
WHERE ((referencia !~~ 'INV%%'::text) AND (estado <> 'EMBARCADO'::text));
"""

with engine.connect() as conn:
    conn.execute(text(sql_drop))
    conn.execute(text(sql_create))
    conn.commit()
    print("View recreated successfully")
