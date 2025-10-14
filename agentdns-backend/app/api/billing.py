from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models.user import User
from ..models.billing import Billing
from ..models.usage import Usage
from ..schemas.billing import Billing as BillingSchema, BillingCreate
from ..schemas.usage import Usage as UsageSchema
from .deps import get_current_active_user
from ..services.billing_service import BillingService

router = APIRouter()


@router.get("/balance")
def get_balance(
    current_user: User = Depends(get_current_active_user)
):
    """Get user balance"""
    return {
        "balance": current_user.balance,
        "currency": "USD"
    }


@router.post("/topup")
def topup_balance(
    billing_data: BillingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Top up account balance"""
    if billing_data.bill_type != "topup":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bill_type must be 'topup'"
        )
    
    if billing_data.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount must be greater than 0"
        )
    
    billing_service = BillingService(db)
    
    try:
        # Simulate payment processing
        # In production, call payment gateway here
        billing_record = billing_service.topup_user(
            user=current_user,
            amount=billing_data.amount,
            payment_method=billing_data.payment_method,
            transaction_id=f"txn_{datetime.utcnow().timestamp()}"
        )
        
        return {
            "message": "Topup succeeded",
            "billing_record": billing_record,
            "new_balance": current_user.balance
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Topup failed: {str(e)}"
        )


@router.get("/history", response_model=List[BillingSchema])
def get_billing_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    bill_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get billing history"""
    query = db.query(Billing).filter(Billing.user_id == current_user.id)
    
    if bill_type:
        query = query.filter(Billing.bill_type == bill_type)
    
    if start_date:
        query = query.filter(Billing.created_at >= start_date)
    
    if end_date:
        query = query.filter(Billing.created_at <= end_date)
    
    bills = query.order_by(Billing.created_at.desc()).offset(skip).limit(limit).all()
    
    return bills


@router.get("/usage", response_model=List[UsageSchema])
def get_usage_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    service_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get usage history"""
    query = db.query(Usage).filter(Usage.user_id == current_user.id)
    
    if service_id:
        query = query.filter(Usage.service_id == service_id)
    
    if start_date:
        query = query.filter(Usage.started_at >= start_date)
    
    if end_date:
        query = query.filter(Usage.started_at <= end_date)
    
    usage_records = query.order_by(Usage.started_at.desc()).offset(skip).limit(limit).all()
    
    # Ensure proper conversion to Pydantic model
    return [UsageSchema.model_validate(record) for record in usage_records]


@router.get("/stats")
def get_billing_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """Get billing statistics"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total spent
    total_spent = db.query(
        func.sum(Billing.amount)
    ).filter(
        Billing.user_id == current_user.id,
        Billing.bill_type == "charge",
        Billing.created_at >= start_date
    ).scalar() or 0
    
    # Total topup
    total_topup = db.query(
        func.sum(Billing.amount)
    ).filter(
        Billing.user_id == current_user.id,
        Billing.bill_type == "topup",
        Billing.created_at >= start_date
    ).scalar() or 0
    
    # Total requests
    total_requests = db.query(
        func.count(Usage.id)
    ).filter(
        Usage.user_id == current_user.id,
        Usage.started_at >= start_date
    ).scalar() or 0
    
    # Spending grouped by service
    service_spending = db.query(
        Usage.service_id,
        func.sum(Usage.cost_amount).label("total_cost"),
        func.count(Usage.id).label("request_count")
    ).filter(
        Usage.user_id == current_user.id,
        Usage.started_at >= start_date
    ).group_by(Usage.service_id).all()
    
    return {
        "period_days": days,
        "current_balance": current_user.balance,
        "total_spent": float(total_spent),
        "total_topup": float(total_topup),
        "total_requests": total_requests,
        "service_spending": [
            {
                "service_id": item.service_id,
                "total_cost": float(item.total_cost),
                "request_count": item.request_count
            }
            for item in service_spending
        ]
    }


@router.post("/refund/{bill_id}")
def request_refund(
    bill_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Request refund"""
    # Find original bill
    original_bill = db.query(Billing).filter(
        Billing.bill_id == bill_id,
        Billing.user_id == current_user.id,
        Billing.bill_type == "charge"
    ).first()
    
    if not original_bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found or not refundable"
        )
    
    # Check if already refunded
    existing_refund = db.query(Billing).filter(
        Billing.user_id == current_user.id,
        Billing.bill_type == "refund",
        Billing.billing_metadata.contains(f"original_bill_id:{bill_id}")
    ).first()
    
    if existing_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This bill has already been refunded"
        )
    
    billing_service = BillingService(db)
    
    try:
        refund_record = billing_service.refund_user(
            user=current_user,
            amount=original_bill.amount,
            description=f"Refund: {original_bill.description}",
            original_bill_id=bill_id
        )
        
        return {
            "message": "Refund succeeded",
            "refund_record": refund_record,
            "new_balance": current_user.balance
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refund failed: {str(e)}"
        ) 