"""
Client usage logs APIs
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc, asc, or_
from pydantic import BaseModel

from ...database import get_db
from ...models.user import User
from ...models.usage import Usage
from ...models.service import Service
from ...models.agent import Agent
from ...api.deps import get_current_client_user

router = APIRouter()


class UsageLogResponse(BaseModel):
    """Usage log response"""
    id: int
    timestamp: datetime
    service_name: str
    service_id: int
    agent_name: str
    agent_id: int
    method: str
    endpoint: str
    status_code: int
    response_time: Optional[int]  # milliseconds
    cost: float
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    error_message: Optional[str]
    ip_address: Optional[str]


class LogStatsResponse(BaseModel):
    """Log statistics response"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time: float
    total_cost: float
    total_tokens: int
    period_start: datetime
    period_end: datetime


class ServiceLogStats(BaseModel):
    """Service log statistics"""
    service_name: str
    service_id: int
    total_calls: int
    successful_calls: int
    failed_calls: int
    total_cost: float
    avg_response_time: float
    success_rate: float


@router.get("/", response_model=List[UsageLogResponse])
async def get_usage_logs(
    service_id: Optional[int] = Query(None, description="Service ID filter"),
    agent_id: Optional[int] = Query(None, description="API key ID filter"),
    status: Optional[str] = Query(None, description="Status filter: success, error"),
    start_date: Optional[datetime] = Query(None, description="Start time"),
    end_date: Optional[datetime] = Query(None, description="End time"),
    search: Optional[str] = Query(None, description="Search keyword"),
    order_by: str = Query("created_at", description="Order by field"),
    order_dir: str = Query("desc", description="Order: asc, desc"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get usage logs list"""
    
    # 构建基础查询
    query = db.query(Usage).filter(Usage.user_id == current_user.id)
    
    # 应用筛选条件
    if service_id:
        query = query.filter(Usage.service_id == service_id)
    
    if agent_id:
        query = query.filter(Usage.agent_id == agent_id)
    
    if status:
        if status == "success":
            query = query.filter(Usage.status.in_(['success', 'completed']))
        elif status == "error":
            query = query.filter(Usage.status.in_(['error', 'failed']))
        else:
            query = query.filter(Usage.status == status)
    
    if start_date:
        query = query.filter(Usage.created_at >= start_date)
    
    if end_date:
        query = query.filter(Usage.created_at <= end_date)
    
    if search:
        # Search by service name or error message
        query = query.join(Service, Usage.service_id == Service.id, isouter=True).filter(
            or_(
                Service.name.ilike(f"%{search}%"),
                Usage.error_message.ilike(f"%{search}%"),
                Usage.endpoint.ilike(f"%{search}%")
            )
        )
    
    # Ordering
    order_column = getattr(Usage, order_by, Usage.created_at)
    if order_dir.lower() == "asc":
        query = query.order_by(asc(order_column))
    else:
        query = query.order_by(desc(order_column))
    
    # Pagination
    usage_logs = query.offset(offset).limit(limit).all()
    
    # Build response
    result = []
    for log in usage_logs:
        # 获取服务信息
        service_name = "Unknown Service"
        if log.service:
            service_name = log.service.name
        
        # 获取Agent信息
        agent_name = "Unknown Agent"
        if log.agent:
            agent_name = log.agent.name
        
        result.append(UsageLogResponse(
            id=log.id,
            timestamp=log.created_at,
            service_name=service_name,
            service_id=log.service_id or 0,
            agent_name=agent_name,
            agent_id=log.agent_id or 0,
            method=log.http_method or "POST",
            endpoint=log.endpoint or "/",
            status_code=log.status_code or 200,
            response_time=log.response_time,
            cost=log.cost or 0.0,
            input_tokens=log.input_tokens,
            output_tokens=log.output_tokens,
            error_message=log.error_message,
            ip_address=log.ip_address
        ))
    
    return result


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats(
    service_id: Optional[int] = Query(None),
    agent_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get log statistics"""
    
    # Default time range: last 30 days
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # 构建查询
    query = db.query(Usage).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= start_date,
            Usage.created_at <= end_date
        )
    )
    
    if service_id:
        query = query.filter(Usage.service_id == service_id)
    
    if agent_id:
        query = query.filter(Usage.agent_id == agent_id)
    
    # Stats
    total_requests = query.count()
    
    successful_requests = query.filter(
        Usage.status.in_(['success', 'completed'])
    ).count()
    
    failed_requests = total_requests - successful_requests
    success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
    
    # Average response time
    avg_response_time = query.filter(
        Usage.response_time.isnot(None)
    ).with_entities(func.avg(Usage.response_time)).scalar() or 0
    
    # Total cost
    total_cost = query.with_entities(func.sum(Usage.cost)).scalar() or 0.0
    
    # Total tokens
    total_tokens = query.with_entities(
        func.sum(Usage.input_tokens) + func.sum(Usage.output_tokens)
    ).scalar() or 0
    
    return LogStatsResponse(
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        success_rate=round(success_rate, 2),
        avg_response_time=round(avg_response_time, 2),
        total_cost=total_cost,
        total_tokens=total_tokens,
        period_start=start_date,
        period_end=end_date
    )


@router.get("/services", response_model=List[ServiceLogStats])
async def get_service_log_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get per-service usage statistics"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Group by service
    service_stats = db.query(
        Usage.service_id,
        Service.name.label('service_name'),
        func.count(Usage.id).label('total_calls'),
        func.sum(
            func.case(
                [(Usage.status.in_(['success', 'completed']), 1)],
                else_=0
            )
        ).label('successful_calls'),
        func.sum(Usage.cost).label('total_cost'),
        func.avg(Usage.response_time).label('avg_response_time')
    ).join(
        Service, Usage.service_id == Service.id, isouter=True
    ).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= start_date
        )
    ).group_by(Usage.service_id, Service.name).all()
    
    result = []
    for stat in service_stats:
        failed_calls = stat.total_calls - stat.successful_calls
        success_rate = (stat.successful_calls / stat.total_calls * 100) if stat.total_calls > 0 else 0
        
        result.append(ServiceLogStats(
            service_name=stat.service_name or "Unknown Service",
            service_id=stat.service_id or 0,
            total_calls=stat.total_calls,
            successful_calls=stat.successful_calls,
            failed_calls=failed_calls,
            total_cost=float(stat.total_cost or 0),
            avg_response_time=float(stat.avg_response_time or 0),
            success_rate=round(success_rate, 2)
        ))
    
    return result


@router.get("/timeline")
async def get_usage_timeline(
    service_id: Optional[int] = Query(None),
    agent_id: Optional[int] = Query(None),
    days: int = Query(7, ge=1, le=90),
    interval: str = Query("hour", description="时间间隔: hour, day"),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get usage timeline data"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 构建基础查询
    query = db.query(Usage).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= start_date
        )
    )
    
    if service_id:
        query = query.filter(Usage.service_id == service_id)
    
    if agent_id:
        query = query.filter(Usage.agent_id == agent_id)
    
    # 根据间隔类型生成时间点
    timeline_data = []
    
    if interval == "hour":
        # Hourly aggregation
        for i in range(days * 24):
            hour_start = start_date + timedelta(hours=i)
            hour_end = hour_start + timedelta(hours=1)
            
            hour_stats = query.filter(
                and_(
                    Usage.created_at >= hour_start,
                    Usage.created_at < hour_end
                )
            ).with_entities(
                func.count(Usage.id).label('calls'),
                func.sum(Usage.cost).label('cost'),
                func.sum(
                    func.case(
                        [(Usage.status.in_(['success', 'completed']), 1)],
                        else_=0
                    )
                ).label('successful_calls')
            ).first()
            
            timeline_data.append({
                "timestamp": hour_start.isoformat(),
                "calls": hour_stats.calls or 0,
                "cost": float(hour_stats.cost or 0),
                "successful_calls": hour_stats.successful_calls or 0,
                "failed_calls": (hour_stats.calls or 0) - (hour_stats.successful_calls or 0)
            })
    
    else:  # day
        # Daily aggregation
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_stats = query.filter(
                and_(
                    Usage.created_at >= day_start,
                    Usage.created_at < day_end
                )
            ).with_entities(
                func.count(Usage.id).label('calls'),
                func.sum(Usage.cost).label('cost'),
                func.sum(
                    func.case(
                        [(Usage.status.in_(['success', 'completed']), 1)],
                        else_=0
                    )
                ).label('successful_calls')
            ).first()
            
            timeline_data.append({
                "date": day_start.strftime('%Y-%m-%d'),
                "calls": day_stats.calls or 0,
                "cost": float(day_stats.cost or 0),
                "successful_calls": day_stats.successful_calls or 0,
                "failed_calls": (day_stats.calls or 0) - (day_stats.successful_calls or 0)
            })
    
    return {
        "interval": interval,
        "period_days": days,
        "data": timeline_data
    }


@router.get("/errors")
async def get_error_logs(
    service_id: Optional[int] = Query(None),
    agent_id: Optional[int] = Query(None),
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get error logs"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Query error logs
    query = db.query(Usage).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= start_date,
            Usage.status.in_(['error', 'failed']),
            Usage.error_message.isnot(None)
        )
    )
    
    if service_id:
        query = query.filter(Usage.service_id == service_id)
    
    if agent_id:
        query = query.filter(Usage.agent_id == agent_id)
    
    error_logs = query.order_by(desc(Usage.created_at)).limit(limit).all()
    
    # Error statistics
    error_stats = db.query(
        Usage.status_code,
        Usage.error_message,
        func.count(Usage.id).label('count')
    ).filter(
        and_(
            Usage.user_id == current_user.id,
            Usage.created_at >= start_date,
            Usage.status.in_(['error', 'failed'])
        )
    ).group_by(Usage.status_code, Usage.error_message).all()
    
    return {
        "period_days": days,
        "total_errors": len(error_logs),
        "error_logs": [
            {
                "id": log.id,
                "timestamp": log.created_at,
                "service_name": log.service.name if log.service else "Unknown",
                "agent_name": log.agent.name if log.agent else "Unknown",
                "status_code": log.status_code,
                "error_message": log.error_message,
                "endpoint": log.endpoint,
                "cost": log.cost or 0.0
            }
            for log in error_logs
        ],
        "error_distribution": [
            {
                "status_code": stat.status_code,
                "error_message": stat.error_message,
                "count": stat.count
            }
            for stat in error_stats
        ]
    }


@router.get("/export")
async def export_usage_logs(
    format: str = Query("csv", description="导出格式: csv, json"),
    service_id: Optional[int] = Query(None),
    agent_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """导出使用日志"""
    
    # 构建查询（与获取日志列表相同的逻辑）
    query = db.query(Usage).filter(Usage.user_id == current_user.id)
    
    if service_id:
        query = query.filter(Usage.service_id == service_id)
    if agent_id:
        query = query.filter(Usage.agent_id == agent_id)
    if start_date:
        query = query.filter(Usage.created_at >= start_date)
    if end_date:
        query = query.filter(Usage.created_at <= end_date)
    
    # 限制导出数量（避免内存问题）
    logs_count = query.count()
    if logs_count > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="导出记录过多，请缩小时间范围或添加筛选条件"
        )
    
    # 生成导出文件名
    export_filename = f"usage_logs_{current_user.id}_{int(datetime.utcnow().timestamp())}.{format}"
    
    return {
        "message": "导出任务已创建",
        "download_url": f"/api/v1/client/logs/download/{export_filename}",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "record_count": logs_count,
        "format": format
    }
