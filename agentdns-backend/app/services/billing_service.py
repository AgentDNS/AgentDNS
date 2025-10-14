from typing import Optional
from sqlalchemy.orm import Session
from decimal import Decimal
import uuid

from ..models.service import Service
from ..models.user import User
from ..models.billing import Billing
from ..models.usage import Usage


class BillingService:
    """Billing service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_cost(
        self,
        service: Service,
        tokens_used: int = 0,
        requests_count: int = 1,
        data_transfer_mb: float = 0.0
    ) -> float:
        """Calculate service usage cost"""
        
        if service.pricing_model == "per_request":
            return float(service.price_per_unit * requests_count)
        
        elif service.pricing_model == "per_token":
            return float(service.price_per_unit * tokens_used / 1000)  # price per 1k tokens
        
        elif service.pricing_model == "per_mb":
            return float(service.price_per_unit * data_transfer_mb)
        
        elif service.pricing_model == "subscription":
            # Subscription: return 0 for now; should check subscription status
            return 0.0
        
        else:
            return float(service.price_per_unit)
    
    def charge_user(
        self,
        user: User,
        amount: float,
        description: str,
        service_name: Optional[str] = None
    ) -> Billing:
        """Charge user"""
        
        if user.balance < amount:
            raise ValueError("Insufficient user balance")
        
        # 扣除余额
        user.balance -= amount
        
        # 创建账单记录
        billing_record = Billing(
            user_id=user.id,
            bill_id=str(uuid.uuid4())[:16],
            bill_type="charge",
            amount=amount,
            description=description,
            service_name=service_name,
            status="completed",
            payment_method="balance"
        )
        
        self.db.add(billing_record)
        self.db.commit()
        self.db.refresh(billing_record)
        
        return billing_record
    
    def refund_user(
        self,
        user: User,
        amount: float,
        description: str,
        original_bill_id: Optional[str] = None
    ) -> Billing:
        """Refund user"""
        
        # 增加余额
        user.balance += amount
        
        # 创建退款记录
        billing_record = Billing(
            user_id=user.id,
            bill_id=str(uuid.uuid4())[:16],
            bill_type="refund",
            amount=amount,
            description=description,
            status="completed",
            payment_method="balance",
            billing_metadata=f"original_bill_id:{original_bill_id}" if original_bill_id else None
        )
        
        self.db.add(billing_record)
        self.db.commit()
        self.db.refresh(billing_record)
        
        return billing_record
    
    def topup_user(
        self,
        user: User,
        amount: float,
        payment_method: str = "credit_card",
        transaction_id: Optional[str] = None
    ) -> Billing:
        """Top up user balance"""
        
        # 增加余额
        user.balance += amount
        
        # 创建充值记录
        billing_record = Billing(
            user_id=user.id,
            bill_id=str(uuid.uuid4())[:16],
            bill_type="topup",
            amount=amount,
            description=f"Account topup {amount} USD",
            status="completed",
            payment_method=payment_method,
            transaction_id=transaction_id
        )
        
        self.db.add(billing_record)
        self.db.commit()
        self.db.refresh(billing_record)
        
        return billing_record 
    
    def record_usage(
        self, 
        user: User, 
        service: Service, 
        amount: float,
        tokens_used: int = 0,
        requests_count: int = 1,
        data_transfer_mb: float = 0.0,
        request_id: Optional[str] = None,
        method: str = "POST",
        execution_time_ms: Optional[int] = None,
        status_code: int = 200,
        request_metadata: Optional[dict] = None
    ) -> Usage:
        """Record service usage and bill"""
        
        # 1) Check balance
        if user.balance < amount:
            raise ValueError("Insufficient user balance")
        
        # 2) Generate request id (if not provided)
        if not request_id:
            request_id = str(uuid.uuid4())[:16]
        
        # 3) Create usage record
        usage_record = Usage(
            user_id=user.id,
            service_id=service.id,
            request_id=request_id,
            method=method,
            endpoint=service.endpoint_url,
            protocol="HTTP",
            tokens_used=tokens_used,
            requests_count=requests_count,
            data_transfer_mb=data_transfer_mb,
            execution_time_ms=execution_time_ms,
            cost_amount=amount,
            status_code=status_code,
            billing_status="charged",
            request_metadata=request_metadata
        )
        
        # 4) Deduct balance
        user.balance -= amount
        
        # 5) Create billing record
        billing_record = Billing(
            user_id=user.id,
            bill_id=str(uuid.uuid4())[:16],
            bill_type="charge",
            amount=amount,
            description=f"使用服务: {service.name}",
            service_name=service.name,
            status="completed",
            payment_method="balance"
        )
        
        # 6) Persist to database
        self.db.add(usage_record)
        self.db.add(billing_record)
        self.db.commit()
        self.db.refresh(usage_record)
        
        return usage_record