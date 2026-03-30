import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def check_security():
    if not DATABASE_URL:
        return

    try:
        engine = create_engine(DATABASE_URL)
        # Check if the view has the security_invoker or security_definer (legacy) aspect
        query = text("""
            SELECT relname, reloptions 
            FROM pg_class 
            WHERE relname = 'wms_aeropuerto';
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query).fetchone()
            if result:
                print(f"View: {result[0]}")
                print(f"Options: {result[1]}")
                if result[1] and 'security_barrier' in str(result[1]):
                    print("Note: security_barrier found")
            else:
                print("View not found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_security()
