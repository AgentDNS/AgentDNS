"""
Client API key management APIs
"""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from pydantic import BaseModel

from ...database import get_db
from ...models.user import User
from ...models.agent import Agent
from ...models.usage import Usage
from ...api.deps import get_current_client_user
from ...core.security import get_password_hash

router = APIRouter()


class ApiKeyCreateRequest(BaseModel):
    """Create API key request"""
    name: str
    permissions: List[str] = ["read"]  # read, write
    daily_limit: int = 1000
    description: Optional[str] = None


class ApiKeyUpdateRequest(BaseModel):
    """Update API key request"""
    name: Optional[str] = None
    permissions: Optional[List[str]] = None
    daily_limit: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ApiKeyResponse(BaseModel):
    """API key response"""
    id: int
    name: str
    api_key: str  # 只在创建时返回完整密钥
    masked_key: str  # 脱敏后的密钥
    permissions: List[str]
    daily_limit: int
    used_today: int
    description: Optional[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    usage_count: int


class ApiKeyListResponse(BaseModel):
    """API key list item response"""
    id: int
    name: str
    masked_key: str
    permissions: List[str]
    daily_limit: int
    used_today: int
    description: Optional[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    usage_count: int


def generate_api_key() -> str:
    """Generate API key"""
    prefix = "ak"
    timestamp = hex(int(datetime.utcnow().timestamp()))[2:]
    random_part = secrets.token_hex(16)
    return f"{prefix}_{timestamp}_{random_part}"


def mask_api_key(api_key: str) -> str:
    """Mask API key for display"""
    if len(api_key) <= 16:
        return api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
    return api_key[:8] + '*' * (len(api_key) - 16) + api_key[-8:]


@router.post("/", response_model=ApiKeyResponse)
async def create_api_key(
    request: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Create API key"""
    
    # Enforce per-user API key limit (max 10)
    existing_count = db.query(func.count(Agent.id)).filter(
        Agent.user_id == current_user.id
    ).scalar()
    
    if existing_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key count limit reached (10)"
        )
    
    # Check name duplication
    existing_key = db.query(Agent).filter(
        and_(
            Agent.user_id == current_user.id,
            Agent.name == request.name
        )
    ).first()
    
    if existing_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key name already exists"
        )
    
    # Generate API key
    api_key = generate_api_key()
    api_key_hash = get_password_hash(api_key)
    
    # Create Agent record
    new_agent = Agent(
        name=request.name,
        description=request.description or "",
        api_key_hash=api_key_hash,
        user_id=current_user.id,
        is_active=True,
        daily_limit=request.daily_limit,
        permissions=",".join(request.permissions)
    )
    
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    return ApiKeyResponse(
        id=new_agent.id,
        name=new_agent.name,
        api_key=api_key,  # only returned at creation
        masked_key=mask_api_key(api_key),
        permissions=request.permissions,
        daily_limit=new_agent.daily_limit,
        used_today=0,
        description=new_agent.description,
        is_active=new_agent.is_active,
        created_at=new_agent.created_at,
        last_used_at=new_agent.last_used_at,
        usage_count=0
    )


@router.get("/", response_model=List[ApiKeyListResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """List API keys"""
    
    agents = db.query(Agent).filter(
        Agent.user_id == current_user.id
    ).order_by(desc(Agent.created_at)).all()
    
    result = []
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for agent in agents:
        # Calculate today's usage
        used_today = db.query(func.count(Usage.id)).filter(
            and_(
                Usage.agent_id == agent.id,
                Usage.created_at >= today
            )
        ).scalar() or 0
        
        # Calculate total usage
        usage_count = db.query(func.count(Usage.id)).filter(
            Usage.agent_id == agent.id
        ).scalar() or 0
        
        # Parse permissions
        permissions = agent.permissions.split(",") if agent.permissions else ["read"]
        
        # Generate masked key (stable format based on ID)
        masked_key = f"ak_****{str(agent.id).zfill(4)}"
        
        result.append(ApiKeyListResponse(
            id=agent.id,
            name=agent.name,
            masked_key=masked_key,
            permissions=permissions,
            daily_limit=agent.daily_limit,
            used_today=used_today,
            description=agent.description,
            is_active=agent.is_active,
            created_at=agent.created_at,
            last_used_at=agent.last_used_at,
            usage_count=usage_count
        ))
    
    return result


@router.get("/{key_id}", response_model=ApiKeyListResponse)
async def get_api_key(
    key_id: int,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get API key details"""
    
    agent = db.query(Agent).filter(
        and_(
            Agent.id == key_id,
            Agent.user_id == current_user.id
        )
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Calculate statistics
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    used_today = db.query(func.count(Usage.id)).filter(
        and_(
            Usage.agent_id == agent.id,
            Usage.created_at >= today
        )
    ).scalar() or 0
    
    usage_count = db.query(func.count(Usage.id)).filter(
        Usage.agent_id == agent.id
    ).scalar() or 0
    
    permissions = agent.permissions.split(",") if agent.permissions else ["read"]
    masked_key = f"ak_****{str(agent.id).zfill(4)}"
    
    return ApiKeyListResponse(
        id=agent.id,
        name=agent.name,
        masked_key=masked_key,
        permissions=permissions,
        daily_limit=agent.daily_limit,
        used_today=used_today,
        description=agent.description,
        is_active=agent.is_active,
        created_at=agent.created_at,
        last_used_at=agent.last_used_at,
        usage_count=usage_count
    )


@router.put("/{key_id}", response_model=ApiKeyListResponse)
async def update_api_key(
    key_id: int,
    request: ApiKeyUpdateRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Update API key"""
    
    agent = db.query(Agent).filter(
        and_(
            Agent.id == key_id,
            Agent.user_id == current_user.id
        )
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API密钥不存在"
        )
    
    # Check name duplication
    if request.name and request.name != agent.name:
        existing = db.query(Agent).filter(
            and_(
                Agent.user_id == current_user.id,
                Agent.name == request.name,
                Agent.id != key_id
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key name already exists"
            )
    
    # Apply updates
    if request.name is not None:
        agent.name = request.name
    if request.permissions is not None:
        agent.permissions = ",".join(request.permissions)
    if request.daily_limit is not None:
        agent.daily_limit = request.daily_limit
    if request.description is not None:
        agent.description = request.description
    if request.is_active is not None:
        agent.is_active = request.is_active
    
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(agent)
    
    # Return updated item
    return await get_api_key(key_id, current_user, db)


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Delete API key"""
    
    agent = db.query(Agent).filter(
        and_(
            Agent.id == key_id,
            Agent.user_id == current_user.id
        )
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Check if there is usage history (optionally keep history)
    usage_count = db.query(func.count(Usage.id)).filter(
        Usage.agent_id == agent.id
    ).scalar() or 0
    
    if usage_count > 0:
        # Soft delete: mark inactive
        agent.is_active = False
        agent.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "message": "API key deactivated (usage history preserved)",
            "deleted": False
        }
    else:
        # Hard delete: no usage history
        db.delete(agent)
        db.commit()
        
        return {
            "message": "API key deleted",
            "deleted": True
        }


@router.post("/{key_id}/regenerate", response_model=ApiKeyResponse)
async def regenerate_api_key(
    key_id: int,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Regenerate API key"""
    
    agent = db.query(Agent).filter(
        and_(
            Agent.id == key_id,
            Agent.user_id == current_user.id
        )
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Generate new API key
    new_api_key = generate_api_key()
    new_api_key_hash = get_password_hash(new_api_key)
    
    # Update key
    agent.api_key_hash = new_api_key_hash
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(agent)
    
    permissions = agent.permissions.split(",") if agent.permissions else ["read"]
    
    return ApiKeyResponse(
        id=agent.id,
        name=agent.name,
        api_key=new_api_key,  # return full key once
        masked_key=mask_api_key(new_api_key),
        permissions=permissions,
        daily_limit=agent.daily_limit,
        used_today=0,  # reset usage after regeneration
        description=agent.description,
        is_active=agent.is_active,
        created_at=agent.created_at,
        last_used_at=agent.last_used_at,
        usage_count=0
    )


@router.get("/{key_id}/usage")
async def get_api_key_usage(
    key_id: int,
    days: int = 7,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get API key usage statistics"""
    
    agent = db.query(Agent).filter(
        and_(
            Agent.id == key_id,
            Agent.user_id == current_user.id
        )
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Calculate time range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Aggregate by day
    usage_by_day = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        daily_usage = db.query(
            func.count(Usage.id).label('calls'),
            func.sum(Usage.cost).label('cost')
        ).filter(
            and_(
                Usage.agent_id == key_id,
                Usage.created_at >= day_start,
                Usage.created_at < day_end
            )
        ).first()
        
        usage_by_day.append({
            "date": day_start.strftime('%Y-%m-%d'),
            "calls": daily_usage.calls or 0,
            "cost": float(daily_usage.cost or 0)
        })
    
    # Service usage distribution
    service_usage = db.query(
        Usage.service_id,
        func.count(Usage.id).label('calls'),
        func.sum(Usage.cost).label('cost')
    ).filter(
        and_(
            Usage.agent_id == key_id,
            Usage.created_at >= start_date
        )
    ).group_by(Usage.service_id).all()
    
    service_stats = []
    for usage in service_usage:
        service_name = "Unknown Service"
        if usage.service_id:
            service = db.query(Service).filter(Service.id == usage.service_id).first()
            if service:
                service_name = service.name
        
        service_stats.append({
            "service": service_name,
            "calls": usage.calls,
            "cost": float(usage.cost or 0)
        })
    
    return {
        "key_id": key_id,
        "key_name": agent.name,
        "period_days": days,
        "usage_by_day": usage_by_day,
        "service_distribution": service_stats,
        "total_calls": sum(day['calls'] for day in usage_by_day),
        "total_cost": sum(day['cost'] for day in usage_by_day)
    }
