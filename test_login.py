import os
import sys
sys.path.append(os.getcwd())

from auth_system.database import get_db
from auth_system.auth import authenticate_user
from dotenv import load_dotenv

load_dotenv()

def test_login(email, password):
    db = next(get_db())
    user = authenticate_user(db, email, password)
    if user:
        print(f"✅ LOGIN SUCCESSFUL: {email} | Role: {user.role}")
    else:
        print(f"❌ LOGIN FAILED: {email}")

if __name__ == "__main__":
    test_login("Cliente_ON", "cliente123")
    test_login("cliente", "cliente123")
