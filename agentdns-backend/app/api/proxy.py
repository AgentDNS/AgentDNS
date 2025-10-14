"""
Refactored proxy API - supports three HTTP modes (sync, stream, async)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import httpx
import json
import uuid
from datetime import datetime
import base64
from cryptography.fernet import Fernet
import logging

from ..database import get_db
from ..models.user import User
from ..models.service import Service
from ..models.organization import Organization
from ..models.async_task import AsyncTask
from .deps import get_current_active_user
from ..services.billing_service import BillingService
from ..core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Decryption key
ENCRYPTION_KEY = settings.ENCRYPTION_KEY
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key()
    logger.warning("ENCRYPTION_KEY not set, using a temporary key (will reset on restart)")
elif isinstance(ENCRYPTION_KEY, str):
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()
cipher_suite = Fernet(ENCRYPTION_KEY)


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key"""
    if not encrypted_key:
        return ""
    try:
        return cipher_suite.decrypt(base64.urlsafe_b64decode(encrypted_key.encode())).decode()
    except:
        return ""


def find_service_by_path(db: Session, agentdns_path: str) -> Service:
    """Find service by path"""
    # First try HTTP Agent by AgentDNS path
    service = db.query(Service).filter(
        Service.agentdns_path == agentdns_path,
        Service.is_active == True
    ).first()
    
    # Fallback to legacy AgentDNS URI
    if not service:
        agentdns_uri = f"agentdns://{agentdns_path}"
        service = db.query(Service).filter(
            Service.agentdns_uri == agentdns_uri,
            Service.is_active == True
        ).first()
        logger.debug(f"Find by URI: {agentdns_uri}")
    else:
        logger.debug(f"Found by path: {agentdns_path}")
    
    return service


def validate_service_access(service: Service, current_user: User, db: Session):
    """Validate service access permission"""
    if not service.is_public:
        organization = db.query(Organization).filter(
            Organization.id == service.organization_id
        ).first()
        if organization and organization.owner_id != current_user.id:
            logger.warning(f"User {current_user.id} has no access to private service {service.id}")
            raise HTTPException(
                status_code=403,
                detail="No permission to access"
            )


def prepare_service_headers(service: Service, user: User) -> dict:
    """Prepare request headers for service"""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": f"AgentDNS-Proxy/1.0 (user:{user.id})"
    }
    
    # Attach service API key
    if service.service_api_key:
        decrypted_key = decrypt_api_key(service.service_api_key)
        if decrypted_key:
            headers["Authorization"] = f"Bearer {decrypted_key}"
    
    return headers


# Async task status route - must be defined before general route to avoid conflicts
@router.get("/tasks/{task_id}")
async def query_async_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Query async task status"""
    logger.info(f"Query async task status: {task_id}")
    
    # Find task
    task = db.query(AsyncTask).filter(
        AsyncTask.id == task_id,
        AsyncTask.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(404, "Task not found")
    
    # If task not finished, update status
    if task.is_active:
        await update_task_status(task, db)
    
    # Return raw adapter response if any; otherwise basic status info
    if task.result_data:
        return task.result_data
    else:
        # If no result_data yet, return basic status
        return {
            "state": task.state,
            "progress": task.progress,
            "error": task.error_message if task.state == "failed" else None
        }


@router.api_route(
    "/{agentdns_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def proxy_request(
    agentdns_path: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unified proxy entry - dispatch by http_mode"""
    
    logger.info(f"Proxy request: {request.method} /{agentdns_path} - user: {current_user.id}")
    
    # Find service
    service = find_service_by_path(db, agentdns_path)
    if not service:
        logger.warning(f"Service not found: {agentdns_path}")
        raise HTTPException(
            status_code=404,
            detail="AgentDNS service not found or disabled"
        )
    
    logger.info(f"Service found: {service.name} (ID: {service.id}) - http_mode: {service.http_mode}")
    
    # Validate permission
    validate_service_access(service, current_user, db)
    
    # Ensure endpoint_url exists
    if not service.endpoint_url:
        logger.error(f"Service {service.id} missing endpoint_url")
        raise HTTPException(
            status_code=500,
            detail="Service configuration error: missing endpoint_url"
        )
    
    # Dispatch based on http_mode
    http_mode = service.http_mode or "sync"  # default to sync
    
    try:
        if http_mode == "sync":
            return await handle_sync_request(service, request, current_user, db)
        elif http_mode == "stream":
            return await handle_stream_request(service, request, current_user, db)
        elif http_mode == "async":
            return await handle_async_request(service, request, current_user, db)
        else:
            # Backward compatibility: default to sync
            logger.warning(f"Unknown http_mode: {http_mode}, using sync")
            return await handle_sync_request(service, request, current_user, db)
    except Exception as e:
        logger.error(f"Failed to process request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_sync_request(service: Service, request: Request, user: User, db: Session):
    """Handle sync request"""
    logger.info(f"Handle sync request: {service.name}")
    
    # 1) Verify balance
    billing_service = BillingService(db)
    if service.price_per_unit > 0:
        if user.balance < service.price_per_unit:
            raise HTTPException(status_code=402, detail="Insufficient balance")
    
    # 2) Read request body
    body = await request.body()
    if body:
        try:
            input_data = json.loads(body)
        except json.JSONDecodeError:
            input_data = {}
    else:
        input_data = {}
    
    # 3) Prepare headers
    headers = prepare_service_headers(service, user)
    
    # 4) Forward request
    target_method = service.http_method or request.method
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.request(
            method=target_method,
            url=service.endpoint_url,
            json=input_data,
            headers=headers,
            params=request.query_params
        )
        response.raise_for_status()
        result = response.json()
    
    # 5) Billing
    if service.price_per_unit > 0:
        billing_service.record_usage(user, service, service.price_per_unit)
    
    # 6) Return result
    return result


async def handle_stream_request(service: Service, request: Request, user: User, db: Session):
    """Handle stream request"""
    logger.info(f"Handle stream request: {service.name}")
    
    body = await request.body()
    if body:
        try:
            input_data = json.loads(body)
        except json.JSONDecodeError:
            input_data = {}
    else:
        input_data = {}
    
    # Ensure streaming
    input_data["stream"] = True
    
    billing_service = BillingService(db)
    if service.price_per_unit > 0:
        if user.balance < service.price_per_unit:
            raise HTTPException(status_code=402, detail="Insufficient balance")
    
    headers = prepare_service_headers(service, user)
    target_method = service.http_method or request.method
    
    async def generate_stream():
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                method=target_method,
                url=service.endpoint_url,
                json=input_data,
                headers=headers
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        yield f"{line}\n"
                
                # Record billing
                if service.price_per_unit > 0:
                    billing_service.record_usage(user, service, service.price_per_unit)
    
    return StreamingResponse(generate_stream(), media_type="text/plain")


async def handle_async_request(service: Service, request: Request, user: User, db: Session):
    """Handle async request"""
    logger.info(f"Handle async request: {service.name}")
    
    if request.method != "POST":
        raise HTTPException(400, "Async service only supports POST to create tasks")
    
    # Create async task
    return await create_async_task(service, request, user, db)


async def create_async_task(service: Service, request: Request, user: User, db: Session):
    """Create async task"""
    body = await request.body()
    if body:
        try:
            input_data = json.loads(body)
        except json.JSONDecodeError:
            input_data = {}
    else:
        input_data = {}
    
    # Generate task id
    task_id = str(uuid.uuid4())
    
    # Pre-check balance against estimated cost
    billing_service = BillingService(db)
    if service.price_per_unit > 0:
        if user.balance < service.price_per_unit:
            raise HTTPException(status_code=402, detail="Insufficient balance")
    
    # Call external API to create task
    headers = prepare_service_headers(service, user)
    target_method = service.http_method or "POST"
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.request(
                method=target_method,
                url=service.endpoint_url,
                json=input_data,
                headers=headers
            )
            response.raise_for_status()
            external_response = response.json()
        
        # Extract external task id
        external_task_id = external_response.get("task_id") or external_response.get("id")
        
        # Persist task record
        task = AsyncTask(
            id=task_id,
            service_id=service.id,
            user_id=user.id,
            state="pending",
            input_data=input_data,
            external_task_id=external_task_id,
            estimated_cost=service.price_per_unit
        )
        db.add(task)
        db.commit()
        
        logger.info(f"Async task created: {task_id} -> {external_task_id}")
        
        # Return task id
        return {"task_id": task_id}
        
    except Exception as e:
        logger.error(f"Failed to create async task: {e}")
        raise HTTPException(500, f"Failed to create async task: {str(e)}")





async def update_task_status(task: AsyncTask, db: Session):
    """Update async task status - pass through adapter's raw response"""
    service = task.service
    
    # Build query URL
    query_url = f"{service.endpoint_url.rstrip('/')}/{task.external_task_id}"
    
    headers = prepare_service_headers(service, task.user)
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(query_url, headers=headers)
            response.raise_for_status()
            status_data = response.json()
        
    # Save adapter's complete response
        task.result_data = status_data
        
        # Extract state from adapter response if present
        adapter_state = status_data.get("state", "unknown").lower()
        
        if adapter_state in ["succeeded", "completed", "success", "finished"]:
            task.state = "succeeded"
            task.completed_at = datetime.utcnow()
            task.progress = 1.0
            
            # Billing
            if not task.is_billed and task.estimated_cost > 0:
                billing = BillingService(db)
                billing.record_usage(task.user, service, task.estimated_cost)
                task.actual_cost = task.estimated_cost
                task.is_billed = True
            
        elif adapter_state in ["failed", "error", "cancelled"]:
            task.state = "failed"
            task.error_message = status_data.get("error") or "Task execution failed"
            task.completed_at = datetime.utcnow()
            
        elif adapter_state in ["running", "processing", "in_progress"]:
            task.state = "running"
            task.progress = status_data.get("progress", task.progress)
            if not task.started_at:
                task.started_at = datetime.utcnow()
        elif adapter_state == "pending":
            task.state = "pending"
        
        db.commit()
        logger.info(f"Task status updated: {task.id} -> {task.state} (adapter state: {adapter_state})")
        
    except Exception as e:
        logger.warning(f"Failed to update task status: {task.id}, error: {e}")
        # Keep original state when query fails
