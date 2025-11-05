from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from database.connection import get_db
from models.user import User
import os

# reuse your utils.auth settings
from utils.auth import SECRET_KEY, ALGORITHM

oauth2_scheme = APIKeyHeader(name="Authorization")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    cred_err = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise cred_err
        # we stored email in sub
        user = db.query(User).filter(User.email == sub).first()
        if not user:
            raise cred_err
        return user
    except JWTError:
        raise cred_err
