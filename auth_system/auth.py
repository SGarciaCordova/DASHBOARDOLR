import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from .models import User

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    pwd_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hash_bytes)

def authenticate_user(db: Session, email: str, password: str):
    """
    Authenticate a user by email and password.
    Handles failed attempts and account locking.
    Returns the User object if successful, None otherwise.
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return None
        
    if user.account_locked:
        # Aquí se podría implementar lógica de desbloqueo por tiempo
        return None 
        
    if verify_password(password, user.password_hash):
        # Reset failed attempts on success
        user.failed_attempts = 0
        user.last_login = datetime.now()
        db.commit()
        return user
    else:
        # Increment failed attempts
        user.failed_attempts += 1
        if user.failed_attempts >= 3:
            user.account_locked = True
        db.commit()
        return None

def register_user(db: Session, email: str, password: str, role: str = "user"):
    """
    Register a new user.
    Returns the new User object or raises an exception if email exists.
    """
    hashed = hash_password(password)
    new_user = User(email=email, password_hash=hashed, role=role)
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except IntegrityError:
        db.rollback()
        raise ValueError("El correo electrónico ya está registrado.")
