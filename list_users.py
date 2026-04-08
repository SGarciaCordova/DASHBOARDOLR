import os
import sys
sys.path.append(os.getcwd())

from auth_system.database import get_db
from auth_system.models import User
from dotenv import load_dotenv

load_dotenv()

def list_users():
    db = next(get_db())
    users = db.query(User).all()
    print("USERS IN DATABASE:")
    for user in users:
        print(f"{user.email} | Role: {user.role} | Locked: {user.account_locked}")

if __name__ == "__main__":
    list_users()
