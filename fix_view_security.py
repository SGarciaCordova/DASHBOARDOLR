import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def fix_view():
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL not found in .env")
        return

    try:
        engine = create_engine(DATABASE_URL)
        
        # 1. DROP VIEW
        # 2. CREATE VIEW (DEFAULT is SECURITY INVOKER)
        # 3. GRANT PERMISSIONS
        sql_fix = [
            "DROP VIEW IF EXISTS public.wms_aeropuerto;",
            """
            CREATE VIEW public.wms_aeropuerto AS
             SELECT docto_id,
                referencia,
                (
                    CASE
                        WHEN (fecha ~ '^\d{4}-\d{2}-\d{2}'::text) THEN (fecha)::timestamp without time zone
                        ELSE NULL::timestamp without time zone
                    END)::date AS fecha,
                (
                    CASE
                        WHEN (fecha ~ '^\d{4}-\d{2}-\d{2}'::text) THEN (fecha)::timestamp without time zone
                        ELSE NULL::timestamp without time zone
                    END)::time without time zone AS hora,
                cliente,
                cantidad_pedida,
                cantidad_surtida,
                tarimas,
                tasa_de_cumplimiento,
                estado
               FROM wms_aeropuerto_raw
              WHERE ((referencia !~~ 'INV%'::text) AND (estado <> 'EMBARCADO'::text));
            """,
            "GRANT SELECT ON public.wms_aeropuerto TO authenticated;",
            "GRANT SELECT ON public.wms_aeropuerto TO anon;",
            "GRANT SELECT ON public.wms_aeropuerto TO service_role;"
        ]

        with engine.connect() as conn:
            for stmt in sql_fix:
                print(f"Executing: {stmt.strip().splitlines()[0]}...")
                conn.execute(text(stmt))
            conn.commit()
            print("\n✅ SECURITY FIX APPLIED: 'wms_aeropuerto' is now SECURITY INVOKER.")

    except Exception as e:
        print(f"❌ Error applying security fix: {e}")

if __name__ == "__main__":
    fix_view()
