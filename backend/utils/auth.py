from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = "mylocaltest"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    try:
        if not isinstance(password, str):
            raise TypeError(f"Expected string, got {type(password)}")

        password = password.strip()
        encoded = password.encode("utf-8")

        if len(encoded) > 72:
            raise ValueError("Password cannot be longer than 72 bytes")

        hashed = pwd_context.hash(password)
        return hashed

    except Exception as e:
        print(f"Error hashing password: {e}")
        raise

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
