from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Agent name
    description = Column(Text)  # Agent description
    api_key = Column(String(500), unique=True, nullable=False)  # AgentDNS API key
    
    # Cost control
    cost_limit_daily = Column(Float, default=0.0)  # daily cost limit
    cost_limit_monthly = Column(Float, default=0.0)  # monthly cost limit
    cost_used_daily = Column(Float, default=0.0)  # used today
    cost_used_monthly = Column(Float, default=0.0)  # used this month
    
    # Status management
    is_active = Column(Boolean, default=True)  # enabled
    is_suspended = Column(Boolean, default=False)  # suspended due to limits
    
    # Config
    allowed_services = Column(JSON)  # allowed services (empty means all)
    rate_limit_per_minute = Column(Integer, default=60)  # requests per minute
    
    # Stats
    total_requests = Column(Integer, default=0)  # total requests
    total_cost = Column(Float, default=0.0)  # total cost
    last_used_at = Column(DateTime(timezone=True))  # last used at
    
    # Metadata
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="agents")
    usage_records = relationship("AgentUsage", back_populates="agent")


class AgentUsage(Base):
    __tablename__ = "agent_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    
    # Request info
    service_name = Column(String(200))  # used service name
    request_method = Column(String(10))  # HTTP method
    request_path = Column(String(500))  # request path
    
    # Cost and performance
    cost = Column(Float, default=0.0)  # cost of this request
    tokens_used = Column(Integer, default=0)  # tokens used
    response_time_ms = Column(Integer)  # response time (ms)
    
    # Status
    status_code = Column(Integer)  # HTTP status code
    error_message = Column(Text)  # error message
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    agent = relationship("Agent", back_populates="usage_records") 