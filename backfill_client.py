import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

def backfill_client():
    with engine.connect() as conn:
        print("Backfilling 'cliente' column in 'entradas'...")
        res = conn.execute(text("UPDATE entradas SET cliente = 'REEBOK' WHERE cliente IS NULL"))
        conn.commit()
        print(f"✓ Updated rows.")

if __name__ == "__main__":
    backfill_client()
