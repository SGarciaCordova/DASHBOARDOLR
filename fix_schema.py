import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

def fix_schema():
    with engine.connect() as conn:
        print("Adding column 'cliente' to 'entradas'...")
        try:
            conn.execute(text("ALTER TABLE entradas ADD COLUMN cliente TEXT"))
            conn.commit()
            print("✓ Column 'cliente' added.")
        except Exception as e:
            if "already exists" in str(e):
                print("! Column 'cliente' already exists.")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    fix_schema()
