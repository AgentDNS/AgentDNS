from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AgentBase(BaseModel):
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")


class AgentCreate(AgentBase):
    cost_limit_daily: float = Field(0.0, ge=0, description="Daily cost limit")
    cost_limit_monthly: float = Field(0.0, ge=0, description="Monthly cost limit")
    allowed_services: Optional[List[str]] = Field(None, description="Allowed services")
    rate_limit_per_minute: int = Field(60, ge=1, le=10000, description="Requests per minute limit")


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    cost_limit_daily: Optional[float] = Field(None, ge=0, description="Daily cost limit")
    cost_limit_monthly: Optional[float] = Field(None, ge=0, description="Monthly cost limit")
    allowed_services: Optional[List[str]] = Field(None, description="Allowed services")
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10000, description="Requests per minute limit")
    is_active: Optional[bool] = Field(None, description="Active state")


class Agent(AgentBase):
    id: int
    api_key: str
    cost_limit_daily: float
    cost_limit_monthly: float
    cost_used_daily: float
    cost_used_monthly: float
    is_active: bool
    is_suspended: bool
    allowed_services: Optional[List[str]]
    rate_limit_per_minute: int
    total_requests: int
    total_cost: float
    last_used_at: Optional[datetime]
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class AgentUsageBase(BaseModel):
    service_name: Optional[str] = None
    request_method: Optional[str] = None
    request_path: Optional[str] = None
    cost: float = 0.0
    tokens_used: int = 0
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None


class AgentUsageCreate(AgentUsageBase):
    agent_id: int


class AgentUsage(AgentUsageBase):
    id: int
    agent_id: int
    requested_at: datetime

    class Config:
        from_attributes = True


class AgentStats(BaseModel):
    """Agent statistics"""
    total_requests: int
    total_cost: float
    daily_requests: int
    daily_cost: float
    monthly_requests: int
    monthly_cost: float
    success_rate: float
    avg_response_time: float
    last_24h_requests: List[dict]  # requests distribution in last 24h
    cost_trend: List[dict]  # cost trend


class AgentMonitoring(BaseModel):
    """Agent monitoring info"""
    agent: Agent
    stats: AgentStats
    recent_usage: List[AgentUsage]
    alerts: List[dict]  # 告警信息 