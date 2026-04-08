import os
import time
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")

print(f"Testing connection to: {db_url[:20]}...")

start = time.time()
try:
    # Use standard connection parameters first
    engine = create_engine(db_url, connect_args={"connect_timeout": 5})
    print(f"Engine created in {time.time() - start:.2f}s")
    
    start_conn = time.time()
    with engine.connect() as conn:
        print(f"Connected in {time.time() - start_conn:.2f}s")
        res = conn.execute(text("SELECT 1")).scalar()
        print(f"Query SELECT 1 result: {res}")
        
except Exception as e:
    print(f"Error: {e}")
