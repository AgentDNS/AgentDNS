"""
Client dashboard APIs - overview endpoints
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from ...database import get_db
from ...models.user import User
from ...models.usage import Usage
from ...models.billing import Billing
from ...models.agent import Agent
from ...api.deps import get_current_client_user
from pydantic import BaseModel

router = APIRouter()


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response"""
    total_calls: int
    total_spent: float
    active_services: int
    success_rate: float
    current_balance: float
    this_month_calls: int
    this_month_spent: float


class ActivityRecord(BaseModel):
    """Activity record"""
    id: int
    type: str  # 'api_call', 'recharge', 'service_subscribe'
    service: str
    timestamp: datetime
    status: str  # 'success', 'error', 'pending'
    cost: float
    description: str


class UsageTrendPoint(BaseModel):
    """Usage trend datapoint"""
    date: str
    calls: int
    cost: float


class DashboardOverviewResponse(BaseModel):
    """Dashboard overview response"""
    stats: DashboardStatsResponse
    recent_activity: List[ActivityRecord]
    usage_trend: List[UsageTrendPoint]


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get dashboard overview data"""
    
    # Time ranges
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 1) Stats
    # Total calls
    total_calls = db.query(func.count(Usage.id)).filter(
        Usage.user_id == current_user.id
    ).scalar() or 0
    
    # Total spent
    total_spent = db.query(func.sum(Usage.cost)).filter(
        Usage.user_id == current_user.id
    ).scalar() or 0.0
    
    # This month's calls
    this_month_calls = db.query(func.count(Usage.id)).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= this_month_start
        )
    ).scalar() or 0
    
    # This month's spent
    this_month_spent = db.query(func.sum(Usage.cost)).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= this_month_start
        )
    ).scalar() or 0.0
    
    # Active services (with usage)
    active_services = db.query(func.count(func.distinct(Usage.service_id))).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= thirty_days_ago
        )
    ).scalar() or 0
    
    # Success rate
    total_calls_30d = db.query(func.count(Usage.id)).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= thirty_days_ago
        )
    ).scalar() or 0
    
    successful_calls = db.query(func.count(Usage.id)).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= thirty_days_ago,
            Usage.status == 'success'
        )
    ).scalar() or 0
    
    success_rate = (successful_calls / total_calls_30d * 100) if total_calls_30d > 0 else 0.0
    
    stats = DashboardStatsResponse(
        total_calls=total_calls,
        total_spent=total_spent,
        active_services=active_services,
        success_rate=round(success_rate, 1),
        current_balance=current_user.balance,
        this_month_calls=this_month_calls,
        this_month_spent=this_month_spent
    )
    
    # 2) Recent activity
    recent_activity = []
    
    # Recent usage records
    recent_usage = db.query(Usage).filter(
        Usage.user_id == current_user.id
    ).order_by(desc(Usage.created_at)).limit(5).all()
    
    for usage in recent_usage:
        service_name = "Unknown Service"
        if usage.service:
            service_name = usage.service.name
        
        recent_activity.append(ActivityRecord(
            id=usage.id,
            type='api_call',
            service=service_name,
            timestamp=usage.created_at,
            status=usage.status or 'success',
            cost=usage.cost or 0.0,
            description=f"调用 {service_name}"
        ))
    
    # Recent topups
    recent_billing = db.query(Billing).filter(
        and_(
            Billing.user_id == current_user.id,
            Billing.type == 'recharge'
        )
    ).order_by(desc(Billing.created_at)).limit(3).all()
    
    for billing in recent_billing:
        recent_activity.append(ActivityRecord(
            id=billing.id,
            type='recharge',
            service='账户充值',
            timestamp=billing.created_at,
            status=billing.status or 'completed',
            cost=billing.amount,
            description=f"账户充值 ¥{billing.amount}"
        ))
    
    # Sort by time
    recent_activity.sort(key=lambda x: x.timestamp, reverse=True)
    recent_activity = recent_activity[:10]  # 只取最近10条
    
    # 3) Usage trend (last 7 days)
    usage_trend = []
    for i in range(6, -1, -1):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        daily_calls = db.query(func.count(Usage.id)).filter(
            and_(
                Usage.user_id == current_user.id,
                Usage.created_at >= date_start,
                Usage.created_at < date_end
            )
        ).scalar() or 0
        
        daily_cost = db.query(func.sum(Usage.cost)).filter(
            and_(
                Usage.user_id == current_user.id,
                Usage.created_at >= date_start,
                Usage.created_at < date_end
            )
        ).scalar() or 0.0
        
        usage_trend.append(UsageTrendPoint(
            date=date.strftime('%Y-%m-%d'),
            calls=daily_calls,
            cost=round(daily_cost, 2)
        ))
    
    return DashboardOverviewResponse(
        stats=stats,
        recent_activity=recent_activity,
        usage_trend=usage_trend
    )


@router.get("/quick-stats")
async def get_quick_stats(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """获取快速统计数据（用于实时更新）"""
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 今日调用次数
    today_calls = db.query(func.count(Usage.id)).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= today_start
        )
    ).scalar() or 0
    
    # 今日消费
    today_spent = db.query(func.sum(Usage.cost)).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= today_start
        )
    ).scalar() or 0.0
    
    return {
        "current_balance": current_user.balance,
        "today_calls": today_calls,
        "today_spent": round(today_spent, 2),
        "last_updated": now.isoformat()
    }
