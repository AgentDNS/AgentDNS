from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
from cryptography.fernet import Fernet
import base64
import os

from ..database import get_db
from ..models.user import User
from ..models.organization import Organization
from ..models.service import Service, ServiceMetadata
from ..schemas.service import (
    ServiceCreate, 
    ServiceUpdate, 
    Service as ServiceSchema
)
from .deps import get_current_active_user
from ..services.embedding_service import EmbeddingService
from ..services.milvus_service import get_milvus_service
from ..core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Encryption key (from settings)
ENCRYPTION_KEY = settings.ENCRYPTION_KEY
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key()
    logger.warning("ENCRYPTION_KEY not set, using a temporary key (will reset on restart)")
elif isinstance(ENCRYPTION_KEY, str):
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()
cipher_suite = Fernet(ENCRYPTION_KEY)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt API key"""
    if not api_key:
        return ""
    return base64.urlsafe_b64encode(cipher_suite.encrypt(api_key.encode())).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key"""
    if not encrypted_key:
        return ""
    try:
        return cipher_suite.decrypt(base64.urlsafe_b64decode(encrypted_key.encode())).decode()
    except:
        return ""


def generate_agentdns_uri(org_name: str, category: str, service_name: str, agentdns_path: str = None) -> str:
    """Generate AgentDNS URI"""
    if agentdns_path:
        # Use custom path if provided
        return f"agentdns://{agentdns_path}"
    else:
        # Default/legacy format
        return f"agentdns://{org_name}/{category}/{service_name}"


def service_to_public_dict(service: Service, include_sensitive: bool = False) -> dict:
    """Convert service model to dict, optionally include sensitive fields"""
    service_dict = {
        "id": service.id,
        "name": service.name,
        "category": service.category,
        "agentdns_uri": service.agentdns_uri,
        "description": service.description,
        "version": service.version,
        "is_active": service.is_active,
        "is_public": service.is_public,
        "protocol": service.protocol,  # single protocol field
        "authentication_required": service.authentication_required,
        "pricing_model": service.pricing_model,
        "price_per_unit": service.price_per_unit,
        "currency": service.currency,
        "tags": service.tags or [],
        "capabilities": service.capabilities or {},
        "organization_id": service.organization_id,
        "created_at": service.created_at,
        "updated_at": service.updated_at,
        
        # HTTP Agent specific fields
        "agentdns_path": service.agentdns_path,
        "http_method": service.http_method,
        "http_mode": service.http_mode,  # HTTP mode
        "input_description": service.input_description,
        "output_description": service.output_description,
    }
    
    # Include sensitive info if requested
    if include_sensitive:
        service_dict["endpoint_url"] = service.endpoint_url
        # Decrypt API key
        if service.service_api_key:
            service_dict["service_api_key"] = decrypt_api_key(service.service_api_key)
        else:
            service_dict["service_api_key"] = None
    
    return service_dict


@router.post("/", response_model=ServiceSchema)
def create_service(
    service_data: ServiceCreate,
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create new service"""
    # Verify org ownership
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.owner_id == current_user.id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization does not exist or no permission"
        )
    
    # Generate AgentDNS URI
    agentdns_uri = generate_agentdns_uri(
        organization.name, 
        service_data.category or "general", 
        service_data.name,
        service_data.agentdns_path
    )
    
    # Check AgentDNS URI uniqueness
    if db.query(Service).filter(Service.agentdns_uri == agentdns_uri).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AgentDNS URI exists, use different service name or path"
        )
    
    # Check custom agentdns_path uniqueness
    if service_data.agentdns_path:
        if db.query(Service).filter(Service.agentdns_path == service_data.agentdns_path).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
            detail="AgentDNS path exists, use different path"
            )
    
    # Encrypt API key
    encrypted_api_key = encrypt_api_key(service_data.service_api_key) if service_data.service_api_key else None
    
    # Create service
    db_service = Service(
        name=service_data.name,
        category=service_data.category,
        agentdns_uri=agentdns_uri,
        description=service_data.description,
        version=service_data.version,
        is_public=service_data.is_public,
        endpoint_url=service_data.endpoint_url,
        protocol=service_data.protocol,  # single protocol field
        authentication_required=service_data.authentication_required,
        pricing_model=service_data.pricing_model,
        price_per_unit=service_data.price_per_unit,
        currency=service_data.currency,
        tags=service_data.tags or [],
        capabilities=service_data.capabilities or {},
        organization_id=organization.id,
        
        # HTTP Agent specific fields
        agentdns_path=service_data.agentdns_path,
        http_method=service_data.http_method,
        http_mode=service_data.http_mode,  # HTTP mode
        input_description=service_data.input_description,
        output_description=service_data.output_description,
        service_api_key=encrypted_api_key
    )
    
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    
    # Create service metadata
    metadata = ServiceMetadata(
        service_id=db_service.id,
        search_keywords=service_data.tags or [],
        status="active"
    )
    db.add(metadata)
    db.commit()
    
    # Generate and store vector in Milvus (only if description exists)
    if db_service.description:
        try:
            embedding_service = EmbeddingService()
            milvus_service = get_milvus_service()
            
            # Prepare data for embedding
            vector_data = {
                'name': db_service.name,
                'category': db_service.category,
                'description': db_service.description,
                'tags': db_service.tags,
                'protocol': db_service.protocol,  # single protocol field
                'http_mode': db_service.http_mode,  # HTTP mode
                'capabilities': db_service.capabilities,
                'organization_name': organization.name
            }
            
            # Create embedding
            embedding = embedding_service.create_service_embedding(vector_data)
            
            # Store in Milvus
            success = milvus_service.insert_service_vector(
                service_id=db_service.id,
                embedding=embedding,
                service_name=db_service.name,
                category=db_service.category or "",
                organization_id=organization.id
            )
            
            if success:
                logger.info(f"Successfully stored vector for service {db_service.id}")
            else:
                logger.warning(f"Failed to store vector for service {db_service.id}")
                
        except Exception as e:
            logger.error(f"Error creating vector for service {db_service.id}: {e}")
            # Do not raise; service creation succeeded and vectorization shouldn't block
    
    # Return public service info
    return ServiceSchema.parse_obj(service_to_public_dict(db_service))


@router.get("/", response_model=List[ServiceSchema])
def list_services(
    organization_id: int = None,
    category: str = None,
    is_public: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List services"""
    query = db.query(Service).filter(Service.is_active == True)
    
    if organization_id:
        query = query.filter(Service.organization_id == organization_id)
    
    if category:
        query = query.filter(Service.category == category)
    
    if is_public is not None:
        query = query.filter(Service.is_public == is_public)
    
    # When listing private services, ensure user has permission
    if not is_public:
        user_org_ids = [org.id for org in db.query(Organization).filter(
            Organization.owner_id == current_user.id
        ).all()]
        query = query.filter(Service.organization_id.in_(user_org_ids))
    
    services = query.offset(skip).limit(limit).all()
    
    # Get org IDs owned by user
    user_org_ids = [org.id for org in db.query(Organization).filter(
        Organization.owner_id == current_user.id
    ).all()]
    
    # Convert to dict; include sensitive fields if owned by the user
    public_services = []
    for service in services:
        include_sensitive = service.organization_id in user_org_ids
        public_services.append(ServiceSchema.parse_obj(service_to_public_dict(service, include_sensitive=include_sensitive)))
    
    return public_services


@router.get("/{service_id}", response_model=ServiceSchema)
def get_service(
    service_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get service details"""
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Check if current user is the owner
    organization = db.query(Organization).filter(
        Organization.id == service.organization_id
    ).first()
    is_owner = organization.owner_id == current_user.id
    
    # Check access permission
    if not service.is_public and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access"
        )
    
    # If owner, include sensitive info; otherwise return public info
    return ServiceSchema.parse_obj(service_to_public_dict(service, include_sensitive=is_owner))


@router.put("/{service_id}", response_model=ServiceSchema)
def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update service"""
    # Find service
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Check permission
    organization = db.query(Organization).filter(
        Organization.id == service.organization_id
    ).first()
    
    if organization.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to modify this service"
        )
    
    # Apply updates
    update_data = service_data.dict(exclude_unset=True)
    
    # Encrypt API key if provided
    if 'service_api_key' in update_data:
        if update_data['service_api_key']:
            update_data['service_api_key'] = encrypt_api_key(update_data['service_api_key'])
        else:
            update_data['service_api_key'] = None
    
    for field, value in update_data.items():
        setattr(service, field, value)
    
    db.commit()
    db.refresh(service)
    
    # Update vector in Milvus (only if description exists)
    if service.description:
        try:
            embedding_service = EmbeddingService()
            milvus_service = get_milvus_service()
            
            # Prepare data for embedding
            vector_data = {
                'name': service.name,
                'category': service.category,
                'description': service.description,
                'tags': service.tags,
                'protocol': service.protocol,  # single protocol field
                'http_mode': service.http_mode,  # HTTP mode
                'capabilities': service.capabilities,
                'organization_name': organization.name
            }
            
            # Create new embedding
            embedding = embedding_service.create_service_embedding(vector_data)
            
            # Update vector in Milvus
            success = milvus_service.update_service_vector(
                service_id=service.id,
                embedding=embedding,
                service_name=service.name,
                category=service.category or "",
                organization_id=organization.id
            )
            
            if success:
                logger.info(f"Successfully updated vector for service {service.id}")
            else:
                logger.warning(f"Failed to update vector for service {service.id}")
                
        except Exception as e:
            logger.error(f"Error updating vector for service {service.id}: {e}")
    
    # Return public service info
    return ServiceSchema.parse_obj(service_to_public_dict(service))


@router.delete("/{service_id}")
def delete_service(
    service_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete service"""
    # Find service
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Check permission
    organization = db.query(Organization).filter(
        Organization.id == service.organization_id
    ).first()
    
    if organization.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to delete this service"
        )
    
    # Delete vector from Milvus
    try:
        milvus_service = get_milvus_service()
        success = milvus_service.delete_service_vector(service.id)
        
        if success:
            logger.info(f"Successfully deleted vector for service {service.id}")
        else:
            logger.warning(f"Failed to delete vector for service {service.id}")
            
    except Exception as e:
        logger.error(f"Error deleting vector for service {service.id}: {e}")
    
    # Soft-delete service
    service.is_active = False
    db.commit()
    
    return {"message": "Service deleted"}