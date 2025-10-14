"""
Client authentication APIs - for customer frontend
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from ...database import get_db
from ...models.user import User
from ...core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token
)
from ...core.config import settings
from ...core.permissions import UserRole
from ...api.deps import get_current_client_user

router = APIRouter()


class ClientRegisterRequest(BaseModel):
    """Client registration request"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str


class ClientLoginResponse(BaseModel):
    """Client login response"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class ClientUserProfile(BaseModel):
    """Client user profile"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    balance: float
    is_active: bool
    is_verified: bool
    created_at: str


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def create_client_user(db: Session, user_data: ClientRegisterRequest) -> User:
    """Create client user"""
    # Check if email exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role="client",  # client user - use string, not enum
        is_active=True,
        is_verified=False,  # new users are unverified by default
        balance=0.0  # initial balance is 0
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_client_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate client user login"""
    user = get_user_by_username(db, username) or get_user_by_email(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    # Allow only client users and admins to login to client
    if user.role not in ["client", "admin"]:
        return None
    return user


@router.post("/register", response_model=ClientUserProfile)
def register_client_user(
    user_data: ClientRegisterRequest,
    db: Session = Depends(get_db)
):
    """Client user registration"""
    try:
        user = create_client_user(db, user_data)
        return ClientUserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            balance=user.balance,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat() if user.created_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=ClientLoginResponse)
def login_client_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Client user login"""
    user = authenticate_client_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return ClientLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "balance": user.balance,
            "is_active": user.is_active,
            "is_verified": user.is_verified
        }
    )


@router.get("/me", response_model=ClientUserProfile)
def get_current_client_profile(
    current_user: User = Depends(get_current_client_user),
):
    """Get current client user profile"""
    return ClientUserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        balance=current_user.balance,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat() if current_user.created_at else ""
    )



