from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OrganizationBase(BaseModel):
    name: str
    domain: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None


class Organization(OrganizationBase):
    id: int
    is_verified: bool
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 