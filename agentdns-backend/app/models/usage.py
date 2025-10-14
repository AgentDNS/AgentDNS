from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Usage(Base):
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    
    # Request info
    request_id = Column(String(64), unique=True, index=True)  # unique request id
    method = Column(String(10))  # HTTP method
    endpoint = Column(String(500))  # endpoint called
    protocol = Column(String(20))  # protocol used (MCP, A2A, ANP)
    
    # Usage stats
    tokens_used = Column(Integer, default=0)  # tokens used
    requests_count = Column(Integer, default=1)  # number of requests
    data_transfer_mb = Column(Float, default=0.0)  # data transfer (MB)
    execution_time_ms = Column(Integer)  # execution time (ms)
    
    # Billing info
    cost_amount = Column(Float, default=0.0)  # cost amount
    cost_currency = Column(String(3), default="USD")
    billing_status = Column(String(20), default="pending")  # pending, charged, failed
    
    # Status
    status_code = Column(Integer)  # HTTP status code
    error_message = Column(Text)  # error message
    request_metadata = Column(JSON)  # extra metadata
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="usage_records")
    service = relationship("Service", back_populates="usage_records") 