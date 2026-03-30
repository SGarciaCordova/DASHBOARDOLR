
import sqlite3
import bcrypt
import os
import sys

# Add the project root to sys.path to import from auth_system
sys.path.append(r"c:\Users\Usuario1\Desktop\Antigravity SGC")
from auth_system.auth import hash_password

db_path = r"c:\Users\Usuario1\Desktop\Antigravity SGC\auth_system\auth.db"
new_password = "153138107<3<3" # From .env

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    hashed = hash_password(new_password)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT email FROM users WHERE email='admin';")
    if cursor.fetchone():
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, 
                failed_attempts = 0, 
                account_locked = 0, 
                locked_until = NULL 
            WHERE email = 'admin';
        """, (hashed,))
        conn.commit()
        print(f"Password for 'admin' has been reset successfully to '{new_password}'.")
        print("Account has been unlocked if it was locked.")
    else:
        print("User 'admin' not found in database. You might need to run create_admin.py.")
    
    conn.close()

# Also clear the lockout_registry.json
lockout_file = r"c:\Users\Usuario1\Desktop\Antigravity SGC\lockout_registry.json"
if os.path.exists(lockout_file):
    try:
        import json
        with open(lockout_file, "r") as f:
            data = json.load(f)
        
        if "admin" in data:
            data["admin"] = {"attempts": 0, "locked_until": None}
            with open(lockout_file, "w") as f:
                json.dump(data, f)
            print("lockout_registry.json for 'admin' cleared.")
    except Exception as e:
        print(f"Error clearing lockout_registry.json: {e}")
