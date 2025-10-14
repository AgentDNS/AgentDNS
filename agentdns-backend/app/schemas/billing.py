from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BillingBase(BaseModel):
    bill_type: str  # charge, refund, topup
    amount: float
    currency: str = "USD"
    description: Optional[str] = None


class BillingCreate(BillingBase):
    service_name: Optional[str] = None
    payment_method: str = "balance"


class Billing(BillingBase):
    id: int
    user_id: int
    bill_id: str
    service_name: Optional[str] = None
    usage_period_start: Optional[datetime] = None
    usage_period_end: Optional[datetime] = None
    status: str
    payment_method: str
    transaction_id: Optional[str] = None
    metadata: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 