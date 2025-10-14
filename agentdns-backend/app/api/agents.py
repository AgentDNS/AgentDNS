from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import List
import logging
import secrets
from datetime import datetime, timedelta

from ..database import get_db
from ..models.user import User
from ..models.agent import Agent, AgentUsage
from ..schemas.agent import (
    AgentCreate, 
    AgentUpdate, 
    Agent as AgentSchema,
    AgentStats,
    AgentMonitoring,
    AgentUsage as AgentUsageSchema
)
from .deps import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)


def generate_api_key() -> str:
    """Generate API key"""
    return f"agent_{secrets.token_urlsafe(32)}"


@router.post("", response_model=AgentSchema)
def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new Agent"""
    # Generate API key
    api_key = generate_api_key()
    
    # Create Agent
    db_agent = Agent(
        name=agent_data.name,
        description=agent_data.description,
        api_key=api_key,
        cost_limit_daily=agent_data.cost_limit_daily,
        cost_limit_monthly=agent_data.cost_limit_monthly,
        allowed_services=agent_data.allowed_services,
        rate_limit_per_minute=agent_data.rate_limit_per_minute,
        user_id=current_user.id
    )
    
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    
    logger.info(f"User {current_user.id} created agent {db_agent.id}")
    return db_agent


@router.get("", response_model=List[AgentSchema])
def list_agents(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's Agents"""
    logger.info(f"Getting agents for user {current_user.id}, skip={skip}, limit={limit}")
    agents = db.query(Agent).filter(
        Agent.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    logger.info(f"Found {len(agents)} agents for user {current_user.id}")
    return agents


@router.get("/{agent_id}", response_model=AgentSchema)
def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get Agent details"""
    agent = db.query(Agent).filter(
        and_(Agent.id == agent_id, Agent.user_id == current_user.id)
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    return agent


@router.put("/{agent_id}", response_model=AgentSchema)
def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update Agent configuration"""
    agent = db.query(Agent).filter(
        and_(Agent.id == agent_id, Agent.user_id == current_user.id)
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Update fields
    update_data = agent_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    
    db.commit()
    db.refresh(agent)
    
    logger.info(f"User {current_user.id} updated agent {agent_id}")
    return agent


@router.delete("/{agent_id}")
def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete Agent"""
    agent = db.query(Agent).filter(
        and_(Agent.id == agent_id, Agent.user_id == current_user.id)
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Delete Agent and its usage records
    db.query(AgentUsage).filter(AgentUsage.agent_id == agent_id).delete()
    db.delete(agent)
    db.commit()
    
    logger.info(f"User {current_user.id} deleted agent {agent_id}")
    return {"message": "Agent deleted"}


@router.post("/{agent_id}/regenerate-key", response_model=AgentSchema)
def regenerate_api_key(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Regenerate API key"""
    agent = db.query(Agent).filter(
        and_(Agent.id == agent_id, Agent.user_id == current_user.id)
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Generate new API key
    agent.api_key = generate_api_key()
    db.commit()
    db.refresh(agent)
    
    logger.info(f"User {current_user.id} regenerated API key for agent {agent_id}")
    return agent


@router.get("/{agent_id}/stats", response_model=AgentStats)
def get_agent_stats(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get Agent statistics"""
    agent = db.query(Agent).filter(
        and_(Agent.id == agent_id, Agent.user_id == current_user.id)
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    now = datetime.utcnow()
    today = now.date()
    this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    yesterday = now - timedelta(days=1)
    
    # Today's stats
    daily_stats = db.query(
        func.count(AgentUsage.id).label('requests'),
        func.coalesce(func.sum(AgentUsage.cost), 0).label('cost')
    ).filter(
        and_(
            AgentUsage.agent_id == agent_id,
            func.date(AgentUsage.requested_at) == today
        )
    ).first()
    
    # This month's stats
    monthly_stats = db.query(
        func.count(AgentUsage.id).label('requests'),
        func.coalesce(func.sum(AgentUsage.cost), 0).label('cost')
    ).filter(
        and_(
            AgentUsage.agent_id == agent_id,
            AgentUsage.requested_at >= this_month
        )
    ).first()
    
    # Success rate
    success_count = db.query(func.count(AgentUsage.id)).filter(
        and_(
            AgentUsage.agent_id == agent_id,
            AgentUsage.status_code.between(200, 299)
        )
    ).scalar()
    
    # Average response time
    avg_response_time = db.query(
        func.avg(AgentUsage.response_time_ms)
    ).filter(
        and_(
            AgentUsage.agent_id == agent_id,
            AgentUsage.response_time_ms.isnot(None)
        )
    ).scalar() or 0
    
    # Requests in last 24h (by hour)
    last_24h_requests = db.query(
        func.date_trunc('hour', AgentUsage.requested_at).label('hour'),
        func.count(AgentUsage.id).label('count')
    ).filter(
        and_(
            AgentUsage.agent_id == agent_id,
            AgentUsage.requested_at >= yesterday
        )
    ).group_by(func.date_trunc('hour', AgentUsage.requested_at)).all()
    
    # Cost trend (last 7 days)
    cost_trend = db.query(
        func.date(AgentUsage.requested_at).label('date'),
        func.coalesce(func.sum(AgentUsage.cost), 0).label('cost')
    ).filter(
        and_(
            AgentUsage.agent_id == agent_id,
            AgentUsage.requested_at >= now - timedelta(days=7)
        )
    ).group_by(func.date(AgentUsage.requested_at)).all()
    
    return AgentStats(
        total_requests=agent.total_requests,
        total_cost=agent.total_cost,
        daily_requests=daily_stats.requests,
        daily_cost=float(daily_stats.cost),
        monthly_requests=monthly_stats.requests,
        monthly_cost=float(monthly_stats.cost),
        success_rate=success_count / max(agent.total_requests, 1) * 100,
        avg_response_time=float(avg_response_time),
        last_24h_requests=[
            {"hour": str(r.hour), "count": r.count} 
            for r in last_24h_requests
        ],
        cost_trend=[
            {"date": str(r.date), "cost": float(r.cost)} 
            for r in cost_trend
        ]
    )


@router.get("/{agent_id}/monitoring", response_model=AgentMonitoring)
def get_agent_monitoring(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get Agent monitoring information"""
    agent = db.query(Agent).filter(
        and_(Agent.id == agent_id, Agent.user_id == current_user.id)
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Get stats
    stats = get_agent_stats(agent_id, current_user, db)
    
    # Get recent usage records
    recent_usage = db.query(AgentUsage).filter(
        AgentUsage.agent_id == agent_id
    ).order_by(AgentUsage.requested_at.desc()).limit(50).all()
    
    # Build alerts
    alerts = []
    
    # Cost alerts
    if agent.cost_limit_daily > 0 and agent.cost_used_daily >= agent.cost_limit_daily * 0.9:
        alerts.append({
            "type": "cost_warning",
            "level": "warning" if agent.cost_used_daily < agent.cost_limit_daily else "danger",
            "message": f"Daily cost reached {agent.cost_used_daily/agent.cost_limit_daily*100:.1f}% of limit"
        })
    
    if agent.cost_limit_monthly > 0 and agent.cost_used_monthly >= agent.cost_limit_monthly * 0.9:
        alerts.append({
            "type": "cost_warning",
            "level": "warning" if agent.cost_used_monthly < agent.cost_limit_monthly else "danger",
            "message": f"Monthly cost reached {agent.cost_used_monthly/agent.cost_limit_monthly*100:.1f}% of limit"
        })
    
    # Status alerts
    if agent.is_suspended:
        alerts.append({
            "type": "status_alert",
            "level": "danger",
            "message": "Agent suspended due to cost limit exceeded"
        })
    elif not agent.is_active:
        alerts.append({
            "type": "status_alert",
            "level": "warning",
            "message": "Agent has been disabled"
        })
    
    return AgentMonitoring(
        agent=agent,
        stats=stats,
        recent_usage=recent_usage,
        alerts=alerts
    )


@router.get("/{agent_id}/usage", response_model=List[AgentUsageSchema])
def get_agent_usage(
    agent_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get Agent usage records"""
    agent = db.query(Agent).filter(
        and_(Agent.id == agent_id, Agent.user_id == current_user.id)
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    usage_records = db.query(AgentUsage).filter(
        AgentUsage.agent_id == agent_id
    ).order_by(AgentUsage.requested_at.desc()).offset(skip).limit(limit).all()
    
    return usage_records 