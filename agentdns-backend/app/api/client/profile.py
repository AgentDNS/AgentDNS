"""
Client profile management APIs
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from ...database import get_db
from ...models.user import User
from ...api.deps import get_current_client_user
from ...core.security import verify_password, get_password_hash

router = APIRouter()


class UserProfileResponse(BaseModel):
    """User profile response"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    balance: float
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]


class UpdateProfileRequest(BaseModel):
    """Update profile request"""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    current_password: str
    new_password: str
    confirm_password: str


class SecuritySettingsResponse(BaseModel):
    """Security settings response"""
    two_factor_enabled: bool
    login_notifications: bool
    api_access_enabled: bool
    last_password_change: Optional[datetime]
    active_sessions: int


@router.get("/", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_client_user)
):
    """Get user profile"""
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        balance=current_user.balance,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at
    )


@router.put("/", response_model=UserProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    
    # Check if email is taken
    if request.email and request.email != current_user.email:
        existing_user = db.query(User).filter(
            User.email == request.email,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被其他用户使用"
            )
    
    # 更新字段
    if request.full_name is not None:
        current_user.full_name = request.full_name
    
    if request.email is not None:
        current_user.email = request.email
        # If email changed, may require re-verification
        if request.email != current_user.email:
            current_user.is_verified = False
    
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(current_user)
    
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        balance=current_user.balance,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Change password"""
    
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Verify new password confirmation
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match"
        )
    
    # Validate new password strength
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )
    
    if request.new_password == request.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as current password"
        )
    
    # 更新密码
    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Password changed successfully",
        "changed_at": datetime.utcnow().isoformat()
    }


@router.get("/security", response_model=SecuritySettingsResponse)
async def get_security_settings(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get security settings"""
    
    # Count active sessions (simplified; should query session table)
    active_sessions = 1  # 当前会话
    
    return SecuritySettingsResponse(
        two_factor_enabled=False,  # 2FA not implemented yet
        login_notifications=True,  # default enabled
        api_access_enabled=True,
        last_password_change=current_user.updated_at,
        active_sessions=active_sessions
    )


@router.post("/verify-email")
async def send_verification_email(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Send verification email"""
    
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    # Should send real email; simulated here
    verification_token = f"verify_{current_user.id}_{int(datetime.utcnow().timestamp())}"
    
    return {
        "message": "Verification email sent",
        "email": current_user.email,
        "expires_in": "24 hours",
        "verification_url": f"https://agentdns.com/verify-email?token={verification_token}"
    }


@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Verify email"""
    
    # Should validate token; simplified here
    if not token.startswith(f"verify_{current_user.id}"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link invalid or expired"
        )
    
    current_user.is_verified = True
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Email verified successfully",
        "verified_at": datetime.utcnow().isoformat()
    }


@router.get("/usage-summary")
async def get_usage_summary(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get user usage summary"""
    
    from ...models.usage import Usage
    from ...models.agent import Agent
    from sqlalchemy import func
    
    # Stats
    total_api_calls = db.query(func.count(Usage.id)).filter(
        Usage.user_id == current_user.id
    ).scalar() or 0
    
    total_spent = db.query(func.sum(Usage.cost)).filter(
        Usage.user_id == current_user.id
    ).scalar() or 0.0
    
    active_api_keys = db.query(func.count(Agent.id)).filter(
        Agent.user_id == current_user.id,
        Agent.is_active == True
    ).scalar() or 0
    
    # Current month stats
    this_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    this_month_calls = db.query(func.count(Usage.id)).filter(
        Usage.user_id == current_user.id,
        Usage.created_at >= this_month_start
    ).scalar() or 0
    
    this_month_spent = db.query(func.sum(Usage.cost)).filter(
        Usage.user_id == current_user.id,
        Usage.created_at >= this_month_start
    ).scalar() or 0.0
    
    # Most used service
    top_service = db.query(
        Usage.service_id,
        func.count(Usage.id).label('usage_count')
    ).filter(
        Usage.user_id == current_user.id
    ).group_by(Usage.service_id).order_by(
        func.count(Usage.id).desc()
    ).first()
    
    top_service_name = "N/A"
    if top_service and top_service.service_id:
        from ...models.service import Service
        service = db.query(Service).filter(Service.id == top_service.service_id).first()
        if service:
            top_service_name = service.name
    
    return {
        "account_info": {
            "username": current_user.username,
            "email": current_user.email,
            "member_since": current_user.created_at.strftime('%Y-%m-%d'),
            "account_status": "Verified" if current_user.is_verified else "Unverified",
            "current_balance": current_user.balance
        },
        "usage_stats": {
            "total_api_calls": total_api_calls,
            "total_spent": total_spent,
            "active_api_keys": active_api_keys,
            "this_month_calls": this_month_calls,
            "this_month_spent": this_month_spent,
            "top_service": top_service_name
        },
        "account_health": {
            "balance_status": "OK" if current_user.balance > 10 else "Low balance",
            "api_usage": "OK" if this_month_calls < 10000 else "High usage",
            "verification_status": "Verified" if current_user.is_verified else "Pending"
        }
    }


@router.delete("/")
async def delete_account(
    password: str,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Delete account (password required)"""
    
    # Verify password
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Check pending items or balance
    if current_user.balance > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Account still has balance ¥{current_user.balance}. Please withdraw or use it first."
        )
    
    # Soft delete: mark inactive rather than deleting
    current_user.is_active = False
    current_user.updated_at = datetime.utcnow()
    
    # Deactivate all API keys
    from ...models.agent import Agent
    db.query(Agent).filter(Agent.user_id == current_user.id).update({
        "is_active": False,
        "updated_at": datetime.utcnow()
    })
    
    db.commit()
    
    return {
        "message": "Account deactivated",
        "deactivated_at": datetime.utcnow().isoformat(),
        "note": "Contact support to restore your account"
    }
