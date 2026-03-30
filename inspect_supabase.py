import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

def inspect_table(table_name):
    print(f"\n--- Columns in '{table_name}' ---")
    query = text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")
    with engine.connect() as conn:
        result = conn.execute(query)
        for row in result:
            print(f"{row[0]}: {row[1]}")

if __name__ == "__main__":
    inspect_table("entradas")
    inspect_table("surtido")
