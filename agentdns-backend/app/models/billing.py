from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Billing(Base):
    __tablename__ = "billing_records"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Billing info
    bill_id = Column(String(64), unique=True, index=True)  # bill id
    bill_type = Column(String(20), nullable=False)  # charge, refund, topup
    amount = Column(Float, nullable=False)  # amount
    currency = Column(String(3), default="USD")
    
    # Descriptions
    description = Column(Text)  # bill description
    service_name = Column(String(100))  # related service name
    usage_period_start = Column(DateTime(timezone=True))  # usage period start
    usage_period_end = Column(DateTime(timezone=True))  # usage period end
    
    # Status
    status = Column(String(20), default="pending")  # pending, completed, failed, cancelled
    payment_method = Column(String(50))  # credit_card, paypal, crypto, balance
    transaction_id = Column(String(100))  # external transaction id
    
    # Metadata
    billing_metadata = Column(String(1000))  # extra info in JSON string
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Relationship
    user = relationship("User") 