from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from models.user import User
from schemas.user import UserCreate, UserLogin, UserResponse
from utils.auth import hash_password, verify_password, create_access_token
from utils.response import success_response, error_response

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=None)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Check for duplicates
        if db.query(User).filter(User.username == user.username).first():
            return error_response("Username already taken")
        if db.query(User).filter(User.email == user.email).first():
            return error_response("Email already registered")

        # Create new user
        hashed_pw = hash_password(user.password)
        new_user = User(username=user.username, email=user.email, hashed_password=hashed_pw)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return success_response("User created successfully", {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email
        })
    except Exception as e:
        return error_response(f"Error creating user: {e}")

@router.post("/login", response_model=None)
def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.username == user.username).first()
        if not db_user or not verify_password(user.password, db_user.hashed_password):
            return error_response("Invalid username or password")

        token = create_access_token({"sub": db_user.username})
        return success_response("Login successful", {"access_token": token, "token_type": "bearer"})
    except Exception as e:
        return error_response(f"Error during login: {e}")
