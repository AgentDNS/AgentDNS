"""
Client service invocation APIs - for customer frontend
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import Dict, Any, Optional
from pydantic import BaseModel
import json
import logging

from ...database import get_db
from ...models.user import User
from ...models.service import Service
from ...models.organization import Organization
from ...core.permissions import (
    PermissionChecker, 
    service_to_client_format
)
from ...api.deps import get_current_client_user

# 复用现有的代理逻辑
from ..proxy import (
    find_service_by_path,
    validate_service_access,
    prepare_service_headers,
    handle_sync_request,
    handle_stream_request,
    handle_async_request
)

router = APIRouter()
logger = logging.getLogger(__name__)


class ServiceCallRequest(BaseModel):
    """Service call request"""
    agentdns_url: str
    input_data: Dict[str, Any]
    method: Optional[str] = "POST"


@router.get("/{service_id}")
async def get_service_details(
    service_id: int,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get service details - client only"""
    logger.info(f"Client user {current_user.id} views service details: {service_id}")
    
    try:
        # Query service
        service = db.query(Service).options(joinedload(Service.organization)).filter(
            Service.id == service_id,
            Service.is_active == True
        ).first()
        
        if not service:
            raise HTTPException(404, "Service not found or disabled")
        
        # Check permission (client can only access public services)
        if not service.is_public:
            raise HTTPException(403, "This service is not public")
        
        # Get organization name
        org_name = service.organization.name if service.organization else "Unknown"
        
        # Convert to client-safe format
        service_data = service_to_client_format(service, org_name)
        
        logger.info(f"Returning service details: {service.name}")
        return service_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get service details failed: {e}")
        raise HTTPException(500, f"Get service details failed: {str(e)}")


@router.post("/call")
async def call_service(
    call_request: ServiceCallRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Call service - client only (sync mode)"""
    logger.info(f"Client user {current_user.id} calls service: {call_request.agentdns_url}")
    
    try:
        # Extract service path
        agentdns_path = call_request.agentdns_url.replace("agentdns://", "")
        
        # Find service
        service = find_service_by_path(db, agentdns_path)
        if not service:
            raise HTTPException(404, "AgentDNS service not found or disabled")
        
        # Validate permission (client can only call public services)
        if not service.is_public:
            raise HTTPException(403, "This service is not public")
        
        # Check user balance
        if service.price_per_unit > 0 and current_user.balance < service.price_per_unit:
            raise HTTPException(402, "Insufficient balance")
        
        # Call by service http_mode
        http_mode = service.http_mode or "sync"
        
        if http_mode == "sync":
            # Mock Request object
            class MockRequest:
                def __init__(self, method: str, body_data: Dict):
                    self.method = method
                    self._body_data = json.dumps(body_data).encode()
                    self.query_params = {}
                
                async def body(self):
                    return self._body_data
            
            mock_request = MockRequest(call_request.method, call_request.input_data)
            result = await handle_sync_request(service, mock_request, current_user, db)
            return result
            
        elif http_mode == "async":
            # Async mode returns task id
            mock_request = MockRequest("POST", call_request.input_data)
            result = await handle_async_request(service, mock_request, current_user, db)
            return result
            
        else:
            # stream mode is not supported via this endpoint
            raise HTTPException(400, "For streaming services, use the streaming endpoint")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Call service failed: {e}")
        raise HTTPException(500, f"Call service failed: {str(e)}")


@router.post("/stream/{agentdns_path:path}")
async def stream_service(
    agentdns_path: str,
    request: Request,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Stream call service - client only"""
    logger.info(f"Client user {current_user.id} streams service: {agentdns_path}")
    
    try:
        # Find service
        service = find_service_by_path(db, agentdns_path)
        if not service:
            raise HTTPException(404, "AgentDNS service not found or disabled")
        
        # Validate permission
        if not service.is_public:
            raise HTTPException(403, "This service is not public")
        
        # Ensure it's stream mode
        if service.http_mode != "stream":
            raise HTTPException(400, "This service does not support streaming")
        
        # Check user balance
        if service.price_per_unit > 0 and current_user.balance < service.price_per_unit:
            raise HTTPException(402, "Insufficient balance")
        
        # Call streaming handler
        return await handle_stream_request(service, request, current_user, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stream call failed: {e}")
        raise HTTPException(500, f"Stream call failed: {str(e)}")


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Query async task status - client only"""
    logger.info(f"Client user {current_user.id} queries task: {task_id}")
    
    try:
        # Reuse existing task status logic
        from ..proxy import query_async_task_status
        return await query_async_task_status(task_id, current_user, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task status failed: {e}")
        raise HTTPException(500, f"Get task status failed: {str(e)}")


@router.get("/resolve/{agentdns_path:path}")
async def resolve_service(
    agentdns_path: str,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Resolve AgentDNS path to service info"""
    logger.info(f"Client user {current_user.id} resolves service: {agentdns_path}")
    
    try:
        # Find service
        service = find_service_by_path(db, agentdns_path)
        if not service:
            raise HTTPException(404, "AgentDNS service not found or disabled")
        
        # Validate permission
        if not service.is_public:
            raise HTTPException(403, "This service is not public")
        
        # Fetch organization info
        organization = db.query(Organization).filter(
            Organization.id == service.organization_id
        ).first()
        org_name = organization.name if organization else "Unknown"
        
        # Convert to Tool format (client-safe)
        from ...core.permissions import service_to_tool_format_safe
        tool_info = service_to_tool_format_safe(service, org_name)
        
        logger.info(f"Resolved: {service.name}")
        return tool_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resolve service failed: {e}")
        raise HTTPException(500, f"Resolve service failed: {str(e)}")


@router.get("/schema/{service_id}")
async def get_service_schema(
    service_id: int,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get service input/output schema"""
    logger.info(f"Client user {current_user.id} gets service schema: {service_id}")
    
    try:
        # Query service
        service = db.query(Service).filter(
            Service.id == service_id,
            Service.is_active == True,
            Service.is_public == True
        ).first()
        
        if not service:
            raise HTTPException(404, "Service not found or inaccessible")
        
        # Return IO descriptions
        schema_info = {
            "service_id": service.id,
            "service_name": service.name,
            "agentdns_uri": service.agentdns_uri,
            "input_schema": service.input_description or "{}",
            "output_schema": service.output_description or "{}",
            "http_method": service.http_method or "POST",
            "http_mode": service.http_mode or "sync",
            "examples": {
                "input": "Refer to input_schema",
                "output": "Refer to output_schema"
            }
        }
        
        logger.info(f"Returning schema: {service.name}")
        return schema_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get service schema failed: {e}")
        raise HTTPException(500, f"Get service schema failed: {str(e)}")


@router.get("/categories/{category}/services")
async def get_services_by_category(
    category: str,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get services by category"""
    logger.info(f"Client user {current_user.id} gets category services: {category}")
    
    try:
        # Query public services for category
        services = db.query(Service).options(joinedload(Service.organization)).filter(
            Service.category == category,
            Service.is_active == True,
            Service.is_public == True
        ).offset(offset).limit(limit).all()
        
        # Convert to client format
        results = []
        for service in services:
            org_name = service.organization.name if service.organization else "Unknown"
            service_data = service_to_client_format(service, org_name)
            results.append(service_data)
        
        logger.info(f"Returning {len(results)} services in category {category}")
        return {
            "category": category,
            "services": results,
            "total": len(results),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Get services by category failed: {e}")
        raise HTTPException(500, f"Get services by category failed: {str(e)}")

