from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from datetime import datetime, timedelta

from ..database import get_db
from ..models.db_models import User, PasswordReset, UserRole
from ..models.schemas import UserCreate, UserLogin, UserResponse, ForgotPasswordRequest, VerifyPinRequest, ResetPasswordRequest
from ..services.security import hash_password, verify_password
from ..services.email import send_pin_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/signup", response_model=UserResponse)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create new user
    hashed_pwd = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_pwd,
        role=UserRole.user
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send welcome email
    send_welcome_email(new_user.email, new_user.username)
    
    return new_user

@router.post("/login", response_model=UserResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    # Find user by email or username
    user = db.query(User).filter(
        (User.email == login_data.username_or_email) | (User.username == login_data.username_or_email)
    ).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # In a real app, you would return a JWT token here
    # For now, we return the user profile
    return user

import random

@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        return {"message": "Success"} # Security: don't reveal email existence
    
    # Generate a 6-digit PIN
    pin = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    
    # Save PIN to database
    reset_entry = PasswordReset(
        user_id=user.id,
        pin=pin,
        expires_at=expires_at
    )
    db.add(reset_entry)
    db.commit()
    
    # Send email
    send_pin_email(request.email, pin)
    print(f"DEBUG: Password reset PIN for {request.email}: {pin}")
    
    return {"message": "Success"}

@router.post("/verify-pin")
def verify_pin(request: VerifyPinRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid request")

    reset_entry = db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.pin == request.pin,
        PasswordReset.expires_at > datetime.utcnow()
    ).order_by(PasswordReset.created_at.desc()).first()
    
    if not reset_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired PIN")
    
    return {"message": "PIN verified successfully"}

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid request")

    # Verify PIN again for security during the final step
    reset_entry = db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.pin == request.pin,
        PasswordReset.expires_at > datetime.utcnow()
    ).order_by(PasswordReset.created_at.desc()).first()
    
    if not reset_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired PIN")
    
    # Update password
    user.password_hash = hash_password(request.new_password)
    
    # Delete all PINs for this user
    db.query(PasswordReset).filter(PasswordReset.user_id == user.id).delete()
    db.commit()
    
    return {"message": "Password successfully reset"}
