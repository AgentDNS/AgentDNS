from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)  # org name, e.g., "openai"
    domain = Column(String(255), unique=True, index=True)  # domain, e.g., "openai.com"
    display_name = Column(String(100))  # display name, e.g., "OpenAI"
    description = Column(Text)
    website = Column(String(255))
    logo_url = Column(String(500))
    is_verified = Column(Boolean, default=False)  # verified or not
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="organizations")
    services = relationship("Service", back_populates="organization") 