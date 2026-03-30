
import sqlite3
import bcrypt
import os

db_path = r"c:\Users\Usuario1\Desktop\Antigravity SGC\auth_system\auth.db"
passwords_to_check = ["153138107<3<3", "scordova123", "admin", "admin123"]

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT password_hash FROM users WHERE email='admin';")
    result = cursor.fetchone()
    
    if result:
        hashed_password = result[0]
        print(f"Stored hash: {hashed_password}")
        
        for pwd in passwords_to_check:
            pwd_bytes = pwd.encode('utf-8')
            hash_bytes = hashed_password.encode('utf-8')
            
            if bcrypt.checkpw(pwd_bytes, hash_bytes):
                print(f"Password '{pwd}' matches!")
            else:
                print(f"Password '{pwd}' DOES NOT match.")
    else:
        print("User 'admin' not found.")
    
    conn.close()
