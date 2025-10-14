"""
Client billing management APIs
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, or_
from pydantic import BaseModel
from decimal import Decimal

from ...database import get_db
from ...models.user import User
from ...models.billing import Billing
from ...models.usage import Usage
from ...api.deps import get_current_client_user

router = APIRouter()


class RechargeRequest(BaseModel):
    """Recharge request"""
    amount: float
    payment_method: str = "alipay"  # alipay, wechat, bank_card
    return_url: Optional[str] = None


class BillingRecord(BaseModel):
    """Billing record"""
    id: int
    type: str  # recharge, usage, refund
    amount: float
    description: str
    status: str  # pending, completed, failed, cancelled
    payment_method: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class BillingStatsResponse(BaseModel):
    """Billing statistics response"""
    current_balance: float
    this_month_spent: float
    this_month_recharged: float
    last_month_spent: float
    total_spent: float
    total_recharged: float
    estimated_monthly_cost: float


class PaymentResponse(BaseModel):
    """Payment response"""
    order_id: str
    payment_url: Optional[str]
    qr_code: Optional[str]
    status: str
    expires_at: datetime


@router.get("/balance")
async def get_balance(
    current_user: User = Depends(get_current_client_user)
):
    """Get account balance"""
    return {
        "balance": current_user.balance,
        "currency": "CNY",
        "last_updated": datetime.utcnow().isoformat()
    }


@router.get("/stats", response_model=BillingStatsResponse)
async def get_billing_stats(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get billing statistics"""
    
    now = datetime.utcnow()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = this_month_start
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    
    # This month's spending
    this_month_spent = db.query(func.sum(Usage.cost)).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= this_month_start
        )
    ).scalar() or 0.0
    
    # This month's recharge
    this_month_recharged = db.query(func.sum(Billing.amount)).filter(
        and_(
            Billing.user_id == current_user.id,
            Billing.type == 'recharge',
            Billing.status == 'completed',
            Billing.created_at >= this_month_start
        )
    ).scalar() or 0.0
    
    # Last month's spending
    last_month_spent = db.query(func.sum(Usage.cost)).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= last_month_start,
            Usage.created_at < last_month_end
        )
    ).scalar() or 0.0
    
    # Total spending
    total_spent = db.query(func.sum(Usage.cost)).filter(
        Usage.user_id == current_user.id
    ).scalar() or 0.0
    
    # Total recharge
    total_recharged = db.query(func.sum(Billing.amount)).filter(
        and_(
            Billing.user_id == current_user.id,
            Billing.type == 'recharge',
            Billing.status == 'completed'
        )
    ).scalar() or 0.0
    
    # Estimated monthly cost (based on last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    recent_spent = db.query(func.sum(Usage.cost)).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= thirty_days_ago
        )
    ).scalar() or 0.0
    
    estimated_monthly_cost = recent_spent  # 简单估算
    
    return BillingStatsResponse(
        current_balance=current_user.balance,
        this_month_spent=this_month_spent,
        this_month_recharged=this_month_recharged,
        last_month_spent=last_month_spent,
        total_spent=total_spent,
        total_recharged=total_recharged,
        estimated_monthly_cost=estimated_monthly_cost
    )


@router.post("/recharge", response_model=PaymentResponse)
async def create_recharge_order(
    request: RechargeRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Create recharge order"""
    
    # Validate amount
    if request.amount < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum recharge is CNY 10"
        )
    
    if request.amount > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Single recharge cannot exceed CNY 10000"
        )
    
    # Create recharge record
    order_id = f"recharge_{int(datetime.utcnow().timestamp())}_{current_user.id}"
    
    billing_record = Billing(
        user_id=current_user.id,
        type='recharge',
        amount=request.amount,
        description=f"账户充值 ¥{request.amount}",
        status='pending',
        payment_method=request.payment_method,
        order_id=order_id
    )
    
    db.add(billing_record)
    db.commit()
    db.refresh(billing_record)
    
    # Simulate payment (should call real gateway)
    payment_url = None
    qr_code = None
    
    if request.payment_method == "alipay":
        payment_url = f"https://openapi.alipay.com/gateway.do?order_id={order_id}"
        qr_code = f"alipay://pay?order_id={order_id}&amount={request.amount}"
    elif request.payment_method == "wechat":
        payment_url = f"https://api.mch.weixin.qq.com/pay/unifiedorder?order_id={order_id}"
        qr_code = f"weixin://pay?order_id={order_id}&amount={request.amount}"
    
    return PaymentResponse(
        order_id=order_id,
        payment_url=payment_url,
        qr_code=qr_code,
        status='pending',
        expires_at=datetime.utcnow() + timedelta(minutes=30)
    )


@router.post("/recharge/{order_id}/complete")
async def complete_recharge(
    order_id: str,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Complete recharge (simulated callback)"""
    
    # Find recharge record
    billing_record = db.query(Billing).filter(
        and_(
            Billing.user_id == current_user.id,
            Billing.order_id == order_id,
            Billing.type == 'recharge',
            Billing.status == 'pending'
        )
    ).first()
    
    if not billing_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recharge order not found or already processed"
        )
    
    # Check expiration
    if billing_record.created_at < datetime.utcnow() - timedelta(hours=1):
        billing_record.status = 'expired'
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recharge order expired"
        )
    
    # Update balance
    current_user.balance += billing_record.amount
    
    # Update record status
    billing_record.status = 'completed'
    billing_record.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Recharge succeeded",
        "amount": billing_record.amount,
        "new_balance": current_user.balance,
        "order_id": order_id
    }


@router.get("/records", response_model=List[BillingRecord])
async def get_billing_records(
    type: Optional[str] = Query(None, description="Record type: recharge, usage, refund"),
    status: Optional[str] = Query(None, description="Status: pending, completed, failed"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get billing records"""
    
    query = db.query(Billing).filter(Billing.user_id == current_user.id)
    
    # 筛选条件
    if type:
        query = query.filter(Billing.type == type)
    
    if status:
        query = query.filter(Billing.status == status)
    
    if start_date:
        query = query.filter(Billing.created_at >= start_date)
    
    if end_date:
        query = query.filter(Billing.created_at <= end_date)
    
    # 分页和排序
    records = query.order_by(desc(Billing.created_at)).offset(offset).limit(limit).all()
    
    return [
        BillingRecord(
            id=record.id,
            type=record.type,
            amount=record.amount,
            description=record.description,
            status=record.status,
            payment_method=record.payment_method,
            created_at=record.created_at,
            completed_at=record.completed_at
        )
        for record in records
    ]


@router.get("/usage-summary")
async def get_usage_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get usage cost summary"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Aggregate usage cost by service
    service_usage = db.query(
        Usage.service_id,
        func.count(Usage.id).label('calls'),
        func.sum(Usage.cost).label('total_cost')
    ).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= start_date
        )
    ).group_by(Usage.service_id).all()
    
    service_stats = []
    for usage in service_usage:
        service_name = "Unknown Service"
        if usage.service_id:
            from ...models.service import Service
            service = db.query(Service).filter(Service.id == usage.service_id).first()
            if service:
                service_name = service.name
        
        service_stats.append({
            "service": service_name,
            "calls": usage.calls,
            "total_cost": float(usage.total_cost or 0),
            "avg_cost_per_call": float(usage.total_cost or 0) / usage.calls if usage.calls > 0 else 0
        })
    
    # Aggregate by day
    daily_usage = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_end = day + timedelta(days=1)
        
        daily_cost = db.query(func.sum(Usage.cost)).filter(
            and_(
                Usage.user_id == current_user.id,
                Usage.created_at >= day,
                Usage.created_at < day_end
            )
        ).scalar() or 0.0
        
        daily_usage.append({
            "date": day.strftime('%Y-%m-%d'),
            "cost": float(daily_cost)
        })
    
    total_cost = sum(stat['total_cost'] for stat in service_stats)
    total_calls = sum(stat['calls'] for stat in service_stats)
    
    return {
        "period_days": days,
        "total_cost": total_cost,
        "total_calls": total_calls,
        "avg_cost_per_call": total_cost / total_calls if total_calls > 0 else 0,
        "service_breakdown": service_stats,
        "daily_usage": daily_usage
    }


@router.get("/export")
async def export_billing_records(
    format: str = Query("csv", description="Export format: csv, excel"),
    type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Export billing records"""
    
    # Build query
    query = db.query(Billing).filter(Billing.user_id == current_user.id)
    
    if type:
        query = query.filter(Billing.type == type)
    if start_date:
        query = query.filter(Billing.created_at >= start_date)
    if end_date:
        query = query.filter(Billing.created_at <= end_date)
    
    records = query.order_by(desc(Billing.created_at)).all()
    
    # Should generate actual file; now return a mock download link
    export_filename = f"billing_records_{current_user.id}_{int(datetime.utcnow().timestamp())}.{format}"
    
    return {
        "message": "Export task created",
        "download_url": f"/api/v1/client/billing/download/{export_filename}",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "record_count": len(records)
    }
