import json
from typing import List, Optional
from sqlalchemy import Column, String, Float, Text, ForeignKey, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class OrganizationModel(Base):
    """组织SQLAlchemy模型"""
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True)
    address = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # 关联关系
    agents = relationship("AgentModel", back_populates="org", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "address": self.address,
            "name": self.name,
            "description": self.description or ""
        }


class AgentModel(Base):
    """Agent SQLAlchemy模型"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True)
    address = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    token_cost = Column(Float, default=0)
    
    # JSON字段
    interfaces = Column(JSON, nullable=False, default=list)
    urls = Column(String(512), nullable=False)
    capabilities = Column(JSON, nullable=False, default=list)
    
    # 外键关系
    organization_address = Column(String(255), ForeignKey("organizations.address"), nullable=False)
    org = relationship("OrganizationModel", back_populates="agents")
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "address": self.address,
            "organization": self.organization_address.split("://")[-1] if "://" in self.organization_address else self.organization_address,
            "description": self.description,
            "interfaces": self.interfaces,
            "urls": self.urls,
            "token_cost": self.token_cost,
            "capabilities": self.capabilities
        } 