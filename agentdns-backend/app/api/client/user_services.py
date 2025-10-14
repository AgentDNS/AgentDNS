"""
Client user services APIs - subscribed/used services management
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from pydantic import BaseModel

from ...database import get_db
from ...models.user import User
from ...models.service import Service
from ...models.usage import Usage
from ...models.organization import Organization
from ...api.deps import get_current_client_user
from ...core.permissions import service_to_client_format

router = APIRouter()


class UserServiceResponse(BaseModel):
    """User service response"""
    id: int
    name: str
    category: str
    provider: str
    status: str  # active, inactive, subscribed
    usage_this_month: int
    cost_this_month: float
    last_used: Optional[datetime]
    subscription_date: Optional[datetime]
    avg_response_time: float
    success_rate: float


class ServiceUsageStats(BaseModel):
    """Service usage statistics"""
    service_id: int
    service_name: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_cost: float
    avg_cost_per_call: float
    first_used: datetime
    last_used: datetime


@router.get("/", response_model=List[UserServiceResponse])
async def get_user_services(
    status: Optional[str] = Query(None, description="Service status filter"),
    category: Optional[str] = Query(None, description="Service category filter"),
    sort_by: str = Query("last_used", description="Sort field"),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get user's used services list"""
    
    # User's used services
    used_services_query = db.query(
        Usage.service_id,
        func.count(Usage.id).label('usage_count'),
        func.sum(Usage.cost).label('total_cost'),
        func.max(Usage.created_at).label('last_used'),
        func.min(Usage.created_at).label('first_used'),
        func.avg(Usage.response_time).label('avg_response_time'),
        func.sum(
            func.case(
                [(Usage.status.in_(['success', 'completed']), 1)],
                else_=0
            )
        ).label('successful_calls')
    ).filter(
        Usage.user_id == current_user.id
    ).group_by(Usage.service_id)
    
    # This month's usage
    this_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    this_month_usage = db.query(
        Usage.service_id,
        func.count(Usage.id).label('this_month_calls'),
        func.sum(Usage.cost).label('this_month_cost')
    ).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= this_month_start
        )
    ).group_by(Usage.service_id).all()
    
    # Build this-month usage dict
    this_month_dict = {
        usage.service_id: {
            'calls': usage.this_month_calls,
            'cost': float(usage.this_month_cost or 0)
        }
        for usage in this_month_usage
    }
    
    used_services = used_services_query.all()
    
    result = []
    for usage_stat in used_services:
        # Get service details
        service = db.query(Service).filter(Service.id == usage_stat.service_id).first()
        if not service:
            continue
        
        # Get organization info
        organization = None
        if service.organization_id:
            organization = db.query(Organization).filter(
                Organization.id == service.organization_id
            ).first()
        
        # This month's usage
        this_month_data = this_month_dict.get(usage_stat.service_id, {'calls': 0, 'cost': 0.0})
        
        # Compute success rate
        success_rate = (usage_stat.successful_calls / usage_stat.usage_count * 100) if usage_stat.usage_count > 0 else 0
        
        # Determine service status
        service_status = "active" if this_month_data['calls'] > 0 else "inactive"
        
        result.append(UserServiceResponse(
            id=service.id,
            name=service.name,
            category=service.category or "其他",
            provider=organization.display_name if organization else "Unknown",
            status=service_status,
            usage_this_month=this_month_data['calls'],
            cost_this_month=this_month_data['cost'],
            last_used=usage_stat.last_used,
            subscription_date=usage_stat.first_used,
            avg_response_time=float(usage_stat.avg_response_time or 0),
            success_rate=round(success_rate, 2)
        ))
    
    # Apply filters
    if status:
        result = [s for s in result if s.status == status]
    
    if category:
        result = [s for s in result if s.category == category]
    
    # Sorting
    if sort_by == "last_used":
        result.sort(key=lambda x: x.last_used or datetime.min, reverse=True)
    elif sort_by == "usage_this_month":
        result.sort(key=lambda x: x.usage_this_month, reverse=True)
    elif sort_by == "cost_this_month":
        result.sort(key=lambda x: x.cost_this_month, reverse=True)
    elif sort_by == "name":
        result.sort(key=lambda x: x.name)
    
    return result


@router.get("/{service_id}/stats", response_model=ServiceUsageStats)
async def get_service_usage_stats(
    service_id: int,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get usage statistics for a service"""
    
    # Ensure the user used this service
    service_usage = db.query(Usage).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.service_id == service_id
        )
    ).first()
    
    if not service_usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No usage records for this service"
        )
    
    # Fetch service info
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Time range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Stats
    stats = db.query(
        func.count(Usage.id).label('total_calls'),
        func.sum(
            func.case(
                [(Usage.status.in_(['success', 'completed']), 1)],
                else_=0
            )
        ).label('successful_calls'),
        func.sum(Usage.cost).label('total_cost'),
        func.min(Usage.created_at).label('first_used'),
        func.max(Usage.created_at).label('last_used')
    ).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.service_id == service_id,
            Usage.created_at >= start_date
        )
    ).first()
    
    total_calls = stats.total_calls or 0
    successful_calls = stats.successful_calls or 0
    failed_calls = total_calls - successful_calls
    total_cost = float(stats.total_cost or 0)
    avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
    
    return ServiceUsageStats(
        service_id=service_id,
        service_name=service.name,
        total_calls=total_calls,
        successful_calls=successful_calls,
        failed_calls=failed_calls,
        total_cost=total_cost,
        avg_cost_per_call=round(avg_cost_per_call, 4),
        first_used=stats.first_used,
        last_used=stats.last_used
    )


@router.get("/{service_id}/timeline")
async def get_service_timeline(
    service_id: int,
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get service usage timeline"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Aggregate by day
    timeline_data = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        day_stats = db.query(
            func.count(Usage.id).label('calls'),
            func.sum(Usage.cost).label('cost'),
            func.sum(
                func.case(
                    [(Usage.status.in_(['success', 'completed']), 1)],
                    else_=0
                )
            ).label('successful_calls'),
            func.avg(Usage.response_time).label('avg_response_time')
        ).filter(
            and_(
                Usage.user_id == current_user.id,
                Usage.service_id == service_id,
                Usage.created_at >= day_start,
                Usage.created_at < day_end
            )
        ).first()
        
        timeline_data.append({
            "date": day_start.strftime('%Y-%m-%d'),
            "calls": day_stats.calls or 0,
            "cost": float(day_stats.cost or 0),
            "successful_calls": day_stats.successful_calls or 0,
            "failed_calls": (day_stats.calls or 0) - (day_stats.successful_calls or 0),
            "avg_response_time": float(day_stats.avg_response_time or 0)
        })
    
    return {
        "service_id": service_id,
        "period_days": days,
        "timeline": timeline_data
    }


@router.get("/categories")
async def get_used_categories(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get categories of services the user used"""
    
    categories = db.query(
        Service.category,
        func.count(func.distinct(Usage.service_id)).label('service_count'),
        func.count(Usage.id).label('total_usage'),
        func.sum(Usage.cost).label('total_cost')
    ).join(
        Usage, Service.id == Usage.service_id
    ).filter(
        Usage.user_id == current_user.id
    ).group_by(Service.category).all()
    
    return [
        {
            "category": cat.category or "Others",
            "service_count": cat.service_count,
            "total_usage": cat.total_usage,
            "total_cost": float(cat.total_cost or 0)
        }
        for cat in categories
    ]


@router.get("/recommendations")
async def get_service_recommendations(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get service recommendations (based on user history)"""
    
    # Get categories used by the user
    used_categories = db.query(Service.category).join(
        Usage, Service.id == Usage.service_id
    ).filter(
        Usage.user_id == current_user.id
    ).distinct().all()
    
    used_category_list = [cat.category for cat in used_categories if cat.category]
    
    # Get service IDs the user hasn't used
    used_service_ids = db.query(Usage.service_id).filter(
        Usage.user_id == current_user.id
    ).distinct().subquery()
    
    # Recommend popular services in same categories
    recommended_services = db.query(Service).filter(
        and_(
            Service.is_public == True,
            Service.is_active == True,
            Service.category.in_(used_category_list) if used_category_list else True,
            ~Service.id.in_(db.query(used_service_ids.c.service_id))
        )
    ).limit(limit).all()
    
    result = []
    for service in recommended_services:
        organization = None
        if service.organization_id:
            organization = db.query(Organization).filter(
                Organization.id == service.organization_id
            ).first()
        
        # Get platform-wide usage stats of the service
        service_stats = db.query(
            func.count(Usage.id).label('total_usage'),
            func.avg(Usage.cost).label('avg_cost')
        ).filter(Usage.service_id == service.id).first()
        
        result.append({
            "id": service.id,
            "name": service.name,
            "category": service.category,
            "description": service.description,
            "provider": organization.display_name if organization else "Unknown",
            "avg_cost": float(service_stats.avg_cost or 0),
            "popularity": service_stats.total_usage or 0,
            "reason": f"Recommended based on your usage of {service.category} services"
        })
    
    return result
