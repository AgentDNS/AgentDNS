from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class UsageBase(BaseModel):
    service_id: int
    method: str = "POST"
    endpoint: str
    protocol: str = "MCP"


class UsageCreate(UsageBase):
    tokens_used: int = 0
    requests_count: int = 1
    data_transfer_mb: float = 0.0
    execution_time_ms: Optional[int] = None
    request_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class Usage(UsageBase):
    id: int
    user_id: int
    request_id: str
    tokens_used: int
    requests_count: int
    data_transfer_mb: float
    execution_time_ms: Optional[int] = None
    cost_amount: float
    cost_currency: str
    billing_status: str
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    request_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True 
        # Exclude SQLAlchemy internal attributes
        exclude = {'metadata', 'registry'} 