from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import os
import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Password hashing setup - use argon2 instead of bcrypt (no 72-byte limitation)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.getenv("BETTER_AUTH_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

def hash_password(password: str) -> str:
    """Hash a password using argon2 (no 72-byte limitation)."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: UUID, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = {"user_id": str(user_id)}

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> Optional[UUID]:
    """Verify a JWT access token and return the user_id."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            return None
        return UUID(user_id)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
