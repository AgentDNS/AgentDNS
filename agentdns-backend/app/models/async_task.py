"""
Async task ORM model
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Float, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class AsyncTask(Base):
    """Async task model"""
    __tablename__ = "async_tasks"
    
    # Primary keys and relations
    id = Column(String(36), primary_key=True)  # UUID task_id
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Task state and data
    state = Column(String(20), default="pending", nullable=False)  # pending, running, succeeded, failed
    input_data = Column(JSON, nullable=False)  # raw input
    result_data = Column(JSON)  # final result
    error_message = Column(Text)  # error message
    progress = Column(Float, default=0.0)  # progress 0.0-1.0
    
    # External task info
    external_task_id = Column(String(200))  # external task id
    external_status = Column(String(50))  # external status
    
    # Billing info
    estimated_cost = Column(Float, default=0.0)  # estimated cost
    actual_cost = Column(Float, default=0.0)  # actual cost
    is_billed = Column(Boolean, default=False)  # billed flag
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))  # task started at
    completed_at = Column(DateTime(timezone=True))  # task completed at
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    service = relationship("Service", back_populates="async_tasks")
    user = relationship("User", back_populates="async_tasks")
    
    def __repr__(self):
        return f"<AsyncTask(id={self.id}, state={self.state}, service_id={self.service_id})>"
    
    def to_dict(self, include_sensitive=False):
        """Convert to dict"""
        result = {
            "task_id": self.id,
            "state": self.state,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }
        
        # Add fields by state
        if self.state == "succeeded":
            result["results"] = self.result_data
            result["cost"] = self.actual_cost
        elif self.state == "failed":
            result["error"] = self.error_message
        
        # Include sensitive fields only when requested
        if include_sensitive:
            result.update({
                "external_task_id": self.external_task_id,
                "external_status": self.external_status,
                "input_data": self.input_data,
                "estimated_cost": self.estimated_cost,
                "is_billed": self.is_billed
            })
        
        return result
    
    @property
    def is_completed(self):
        """Check whether task is completed"""
        return self.state in ["succeeded", "failed"]
    
    @property
    def is_active(self):
        """Check whether task is still active"""
        return self.state in ["pending", "running"]
