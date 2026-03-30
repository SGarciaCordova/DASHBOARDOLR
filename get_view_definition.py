import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_view_definition():
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL not found in .env")
        return

    try:
        engine = create_engine(DATABASE_URL)
        # Query to get the definition of a view in PostgreSQL
        query = text("""
            SELECT definition 
            FROM pg_views 
            WHERE schemaname = 'public' 
            AND viewname = 'wms_aeropuerto';
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query).fetchone()
            if result:
                definition = result[0]
                with open("wms_aeropuerto_definition.sql", "w") as f:
                    f.write(f"CREATE OR REPLACE VIEW public.wms_aeropuerto AS\n{definition};")
                print("✅ View definition saved to 'wms_aeropuerto_definition.sql'")
            else:
                print("❌ No view 'wms_aeropuerto' found in schema 'public'.")

    except Exception as e:
        print(f"❌ Error fetching view definition: {e}")

if __name__ == "__main__":
    get_view_definition()
