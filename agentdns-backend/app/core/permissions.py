"""
Permission control - differentiate admin and client permissions
"""

from enum import Enum
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.user import User
from ..models.service import Service
from ..models.organization import Organization


class UserRole(str, Enum):
    """User roles"""
    ADMIN = "admin"                    # system administrator
    CLIENT = "client"                  # client user
    ORGANIZATION_OWNER = "org_owner"   # organization owner


class PermissionChecker:
    """Permission checker"""
    
    @staticmethod
    def check_admin_access(user: User) -> None:
        """Check admin permission"""
        if not user or user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required"
            )
    
    @staticmethod
    def check_client_access(user: User) -> None:
        """Check client access permission"""
        if not user or user.role not in ["client", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
    
    @staticmethod
    def check_service_access(user: User, service: Service, db: Session) -> None:
        """Check service access permission"""
        # Admin can access all services
        if user.role == "admin":
            return
            
        # Public services are accessible to everyone
        if service.is_public:
            return
            
        # Private services are accessible to organization members only
        if service.organization_id:
            organization = db.query(Organization).filter(
                Organization.id == service.organization_id
            ).first()
            
            if organization and organization.owner_id == user.id:
                return
                
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to access this service"
        )
    
    @staticmethod
    def filter_services_by_permission(services: List[Service], user: User) -> List[Service]:
        """Filter services by permission"""
        if user.role == "admin":
            return services
            
        # Client users can only see public services
        return [s for s in services if s.is_public]
    
    @staticmethod
    def can_manage_service(user: User, service: Service, db: Session) -> bool:
        """Check whether user can manage the service"""
        # Admin can manage all services
        if user.role == "admin":
            return True
            
        # Organization owner can manage services of their org
        if service.organization_id:
            organization = db.query(Organization).filter(
                Organization.id == service.organization_id
            ).first()
            return organization and organization.owner_id == user.id
            
        return False


def service_to_client_format(service: Service, organization_name: str = None) -> dict:
    """Convert service to client-safe dict without sensitive fields"""
    return {
        "id": service.id,
        "name": service.name,
        "category": service.category,
        "agentdns_uri": service.agentdns_uri,
        "agentdns_path": service.agentdns_path,
        "description": service.description,
        "version": service.version,
        "is_active": service.is_active,
        "is_public": service.is_public,
        "protocol": service.protocol,
        "http_method": service.http_method,
        "http_mode": service.http_mode,
        "input_description": service.input_description,
        "output_description": service.output_description,
        "authentication_required": service.authentication_required,
        "pricing_model": service.pricing_model,
        "price_per_unit": service.price_per_unit,
        "currency": service.currency,
        "tags": service.tags or [],
        "capabilities": service.capabilities or {},
        "organization_name": organization_name,
        "created_at": service.created_at,
        "updated_at": service.updated_at,
        # Note: exclude sensitive fields
        # - endpoint_url
        # - service_api_key
        # - organization_id
    }


def service_to_tool_format_safe(service: Service, organization_name: str = None) -> dict:
    """Convert service to client-safe Tool format"""
    cost_description_map = {
        "per_request": "Billed per request",
        "per_token": "Billed per token", 
        "per_mb": "Billed per MB transferred",
        "monthly": "Billed monthly",
        "yearly": "Billed yearly"
    }
    
    pricing_model = service.pricing_model or "per_request"
    
    return {
        "name": service.name or "",
        "description": service.description or "",
        "organization": organization_name or "Unknown",
        "agentdns_url": service.agentdns_uri or "",
        "cost": {
            "type": pricing_model,
            "price": str(service.price_per_unit or 0.0),
            "currency": service.currency or "CNY",
            "description": cost_description_map.get(pricing_model, "Billed per request")
        },
        "protocol": service.protocol or "HTTP",
        "method": service.http_method or "POST",
        "http_mode": service.http_mode,
        "input_description": service.input_description or "{}",
        "output_description": service.output_description or "{}"
    }

