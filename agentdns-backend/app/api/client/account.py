"""
Client account management APIs - for customer frontend
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import logging

from ...database import get_db
from ...models.user import User
from ...models.usage import Usage
from ...models.billing import Billing
from ...services.billing_service import BillingService
from ...api.deps import get_current_client_user

router = APIRouter()
logger = logging.getLogger(__name__)


class AccountBalance(BaseModel):
    """Account balance info"""
    balance: float
    currency: str = "CNY"
    last_updated: str


class TopupRequest(BaseModel):
    """Topup request"""
    amount: float
    payment_method: str = "credit_card"


class UsageRecord(BaseModel):
    """Usage record"""
    id: int
    service_name: str
    agentdns_uri: str
    cost: float
    currency: str
    tokens_used: Optional[int]
    request_method: str
    created_at: str


class BillingRecord(BaseModel):
    """Billing record"""
    id: int
    bill_type: str
    amount: float
    currency: str
    description: str
    status: str
    created_at: str


class UsageStats(BaseModel):
    """Usage statistics"""
    total_requests: int
    total_cost: float
    total_tokens: int
    period_days: int
    top_services: List[dict]


@router.get("/profile")
async def get_account_profile(
    current_user: User = Depends(get_current_client_user)
):
    """Get account info"""
    logger.info(f"客户端用户 {current_user.id} 获取账户信息")
    
    try:
        return {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "balance": current_user.balance,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else "",
            "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else ""
        }
    except Exception as e:
        logger.error(f"Get account profile failed: {e}")
        raise HTTPException(500, f"Get account profile failed: {str(e)}")


@router.get("/balance", response_model=AccountBalance)
async def get_account_balance(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get account balance"""
    logger.info(f"客户端用户 {current_user.id} 查询余额")
    
    try:
        # Refresh to fetch latest balance
        db.refresh(current_user)
        
        return AccountBalance(
            balance=current_user.balance,
            currency="CNY",
            last_updated=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Get balance failed: {e}")
        raise HTTPException(500, f"Get balance failed: {str(e)}")


@router.post("/topup")
async def topup_account(
    topup_request: TopupRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Top up account"""
    logger.info(f"Client user {current_user.id} topup: {topup_request.amount}")
    
    if topup_request.amount <= 0:
        raise HTTPException(400, "Topup amount must be greater than 0")
    
    if topup_request.amount > 10000:
        raise HTTPException(400, "Single topup amount cannot exceed CNY 10000")
    
    try:
        # Use billing service for topup
        billing_service = BillingService(db)
        
        # Create billing record
        billing_record = Billing(
            user_id=current_user.id,
            bill_type="topup",
            amount=topup_request.amount,
            currency="CNY",
            description=f"Account topup - {topup_request.payment_method}",
            status="completed",  # simplified; should integrate payment gateway
            payment_method=topup_request.payment_method
        )
        
        db.add(billing_record)
        
        # Update user balance
        current_user.balance += topup_request.amount
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Topup succeeded, user {current_user.id} balance: {current_user.balance}")
        
        return {
            "success": True,
            "message": "Topup succeeded",
            "amount": topup_request.amount,
            "new_balance": current_user.balance,
            "transaction_id": billing_record.id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Topup failed: {e}")
        raise HTTPException(500, f"Topup failed: {str(e)}")


@router.get("/usage", response_model=List[UsageRecord])
async def get_usage_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get usage history"""
    logger.info(f"Client user {current_user.id} queries usage history")
    
    try:
        # Build query
        query = db.query(Usage).filter(Usage.user_id == current_user.id)
        
        # Filter by service name
        if service_name:
            query = query.join(Usage.service).filter(
                func.lower(Usage.service.name).contains(service_name.lower())
            )
        
        # Filter by time range
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Usage.created_at >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Usage.created_at <= end_dt)
        
        # Order and pagination
        usage_records = query.order_by(Usage.created_at.desc()).offset(offset).limit(limit).all()
        
        # Convert to response
        results = []
        for record in usage_records:
            results.append(UsageRecord(
                id=record.id,
                service_name=record.service.name if record.service else "Unknown",
                agentdns_uri=record.service.agentdns_uri if record.service else "",
                cost=record.cost,
                currency=record.currency or "CNY",
                tokens_used=record.tokens_used,
                request_method=record.request_method or "POST",
                created_at=record.created_at.isoformat() if record.created_at else ""
            ))
        
        logger.info(f"Returning {len(results)} usage records")
        return results
        
    except Exception as e:
        logger.error(f"Get usage history failed: {e}")
        raise HTTPException(500, f"Get usage history failed: {str(e)}")


@router.get("/billing", response_model=List[BillingRecord])
async def get_billing_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    bill_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get billing history"""
    logger.info(f"Client user {current_user.id} queries billing history")
    
    try:
        # Build query
        query = db.query(Billing).filter(Billing.user_id == current_user.id)
        
        # Filter by bill type
        if bill_type:
            query = query.filter(Billing.bill_type == bill_type)
        
        # Order and pagination
        billing_records = query.order_by(Billing.created_at.desc()).offset(offset).limit(limit).all()
        
        # Convert to response
        results = []
        for record in billing_records:
            results.append(BillingRecord(
                id=record.id,
                bill_type=record.bill_type,
                amount=record.amount,
                currency=record.currency or "CNY",
                description=record.description or "",
                status=record.status,
                created_at=record.created_at.isoformat() if record.created_at else ""
            ))
        
        logger.info(f"Returning {len(results)} billing records")
        return results
        
    except Exception as e:
        logger.error(f"Get billing history failed: {e}")
        raise HTTPException(500, f"Get billing history failed: {str(e)}")


@router.get("/stats", response_model=UsageStats)
async def get_usage_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get usage statistics"""
    logger.info(f"Client user {current_user.id} queries usage stats")
    
    try:
        # Time range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query records in time range
        usage_query = db.query(Usage).filter(
            Usage.user_id == current_user.id,
            Usage.created_at >= start_date,
            Usage.created_at <= end_date
        )
        
        # Totals
        total_requests = usage_query.count()
        total_cost = usage_query.with_entities(func.sum(Usage.cost)).scalar() or 0.0
        total_tokens = usage_query.with_entities(func.sum(Usage.tokens_used)).scalar() or 0
        
        # Top services
        top_services_query = db.query(
            Usage.service_id,
            func.count(Usage.id).label('usage_count'),
            func.sum(Usage.cost).label('total_cost')
        ).filter(
            Usage.user_id == current_user.id,
            Usage.created_at >= start_date,
            Usage.created_at <= end_date
        ).group_by(Usage.service_id).order_by(func.count(Usage.id).desc()).limit(5)
        
        top_services = []
        for service_id, usage_count, service_cost in top_services_query:
            if service_id:
                from ...models.service import Service
                service = db.query(Service).filter(Service.id == service_id).first()
                if service:
                    top_services.append({
                        "service_name": service.name,
                        "agentdns_uri": service.agentdns_uri,
                        "usage_count": usage_count,
                        "total_cost": float(service_cost or 0.0)
                    })
        
        return UsageStats(
            total_requests=total_requests,
            total_cost=float(total_cost),
            total_tokens=int(total_tokens),
            period_days=days,
            top_services=top_services
        )
        
    except Exception as e:
        logger.error(f"Get usage stats failed: {e}")
        raise HTTPException(500, f"Get usage stats failed: {str(e)}")


@router.get("/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get user's API keys (for SDK usage)"""
    logger.info(f"Client user {current_user.id} queries API keys")
    
    try:
        # Query user's Agents (API keys)
        from ...models.agent import Agent
        agents = db.query(Agent).filter(
            Agent.user_id == current_user.id,
            Agent.is_active == True
        ).all()
        
        # Return API keys (masked)
        api_keys = []
        for agent in agents:
            # 只显示API密钥的前8位和后4位
            masked_key = f"{agent.api_key[:8]}...{agent.api_key[-4:]}" if len(agent.api_key) > 12 else agent.api_key
            
            api_keys.append({
                "id": agent.id,
                "name": agent.name,
                "api_key_masked": masked_key,
                "is_active": agent.is_active,
                "cost_limit_daily": agent.cost_limit_daily,
                "cost_limit_monthly": agent.cost_limit_monthly,
                "cost_used_daily": agent.cost_used_daily,
                "cost_used_monthly": agent.cost_used_monthly,
                "total_requests": agent.total_requests,
                "total_cost": agent.total_cost,
                "last_used_at": agent.last_used_at.isoformat() if agent.last_used_at else None,
                "created_at": agent.created_at.isoformat() if agent.created_at else ""
            })
        
        logger.info(f"Returning {len(api_keys)} API keys")
        return api_keys
        
    except Exception as e:
        logger.error(f"Get API keys failed: {e}")
        raise HTTPException(500, f"Get API keys failed: {str(e)}")


@router.post("/api-keys")
async def create_api_key(
    key_name: str,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Create new API key"""
    logger.info(f"Client user {current_user.id} creates API key: {key_name}")
    
    try:
        from ...models.agent import Agent
        import secrets
        
        # Generate new API key
        api_key = f"agent_{secrets.token_urlsafe(32)}"
        
        # Create Agent record
        agent = Agent(
            name=key_name,
            description=f"客户端API密钥 - {key_name}",
            api_key=api_key,
            user_id=current_user.id,
            is_active=True,
            cost_limit_daily=100.0,  # 默认每日限额
            cost_limit_monthly=1000.0  # 默认每月限额
        )
        
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        logger.info(f"API key created: {agent.id}")
        
        return {
            "success": True,
            "message": "API key created",
            "agent_id": agent.id,
            "name": agent.name,
            "api_key": api_key,  # only returned at creation
            "created_at": agent.created_at.isoformat() if agent.created_at else ""
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Create API key failed: {e}")
        raise HTTPException(500, f"Create API key failed: {str(e)}")

