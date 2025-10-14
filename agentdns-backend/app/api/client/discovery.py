"""
Client service discovery APIs - for customer frontend
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel
import logging

from ...database import get_db
from ...models.user import User
from ...models.service import Service
from ...models.organization import Organization
from ...services.search_engine import SearchEngine
from ...core.permissions import (
    PermissionChecker, 
    service_to_client_format, 
    service_to_tool_format_safe
)
from ...api.deps import get_current_client_user

router = APIRouter()
logger = logging.getLogger(__name__)


class ServiceSearchRequest(BaseModel):
    """Client service search request"""
    query: str
    category: Optional[str] = None
    organization: Optional[str] = None
    protocol: Optional[str] = None
    max_price: Optional[float] = None
    limit: int = 10
    return_tool_format: bool = True


class ServiceSearchResponse(BaseModel):
    """Client service search response"""
    tools: List[dict] = []
    services: List[dict] = []
    total: int = 0
    query: str


@router.post("/search", response_model=ServiceSearchResponse)
async def search_services(
    search_request: ServiceSearchRequest,
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """
    Intelligent AI service search - client only.
    Supports natural language search, returns public services only.
    """
    logger.info(f"Client user {current_user.id} searches services: {search_request.query}")
    
    try:
        # Create search engine
        search_engine = SearchEngine(db)
        
        # Execute search (client can only search public services)
        results, total = search_engine.search(
            query=search_request.query,
            category=search_request.category,
            organization=search_request.organization,
            protocol=search_request.protocol,
            max_price=search_request.max_price,
            limit=search_request.limit,
            return_tool_format=search_request.return_tool_format
        )
        
        logger.info(f"Search done, returned {len(results)} services")
        
        # Build response by format
        if search_request.return_tool_format:
            return ServiceSearchResponse(
                tools=results,
                services=[],
                total=total,
                query=search_request.query
            )
        else:
            return ServiceSearchResponse(
                tools=[],
                services=results,
                total=total,
                query=search_request.query
            )
            
    except Exception as e:
        logger.error(f"Search services failed: {e}")
        raise HTTPException(500, f"Search failed: {str(e)}")


@router.get("/trending")
async def get_trending_services(
    limit: int = Query(10, ge=1, le=50),
    return_tool_format: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get trending services - based on usage (no auth)"""
    logger.info(f"Get trending services, limit: {limit}")
    
    try:
        # Query public and active services, order by created_at (simple trending)
        services_query = db.query(Service).filter(
            Service.is_active == True,
            Service.is_public == True
        ).options(joinedload(Service.organization)).order_by(
            Service.created_at.desc()
        ).limit(limit)
        
        services = services_query.all()
        
        # Convert to client format
        if return_tool_format:
            results = []
            for service in services:
                org_name = service.organization.name if service.organization else "Unknown"
                tool = service_to_tool_format_safe(service, org_name)
                results.append(tool)
        else:
            results = []
            for service in services:
                org_name = service.organization.name if service.organization else "Unknown"
                service_dict = service_to_client_format(service, org_name)
                results.append(service_dict)
        
        logger.info(f"Returning {len(results)} trending services")
        return results
        
    except Exception as e:
        logger.error(f"Get trending services failed: {e}")
        raise HTTPException(500, f"Get trending services failed: {str(e)}")


@router.get("/categories")
async def get_service_categories(
    db: Session = Depends(get_db)
):
    """Get service categories (no auth)"""
    try:
        # Query categories of public services
        categories = db.query(Service.category).filter(
            Service.is_active == True,
            Service.is_public == True,
            Service.category.isnot(None)
        ).distinct().all()
        
        # Extract category names
        category_list = [cat[0] for cat in categories if cat[0]]
        category_list.sort()
        
        logger.info(f"Returning {len(category_list)} categories")
        return category_list
        
    except Exception as e:
        logger.error(f"Get categories failed: {e}")
        raise HTTPException(500, f"Get categories failed: {str(e)}")


@router.get("/organizations")
async def get_service_organizations(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get organizations providing public services"""
    try:
        # Query organizations with public services
        organizations = db.query(Organization).join(Service).filter(
            Service.is_active == True,
            Service.is_public == True
        ).distinct().all()
        
        org_list = [{"id": org.id, "name": org.name} for org in organizations]
        org_list.sort(key=lambda x: x["name"])
        
        logger.info(f"Returning {len(org_list)} organizations")
        return org_list
        
    except Exception as e:
        logger.error(f"Get organizations failed: {e}")
        raise HTTPException(500, f"Get organizations failed: {str(e)}")


@router.get("/protocols")
async def get_supported_protocols(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get supported protocols"""
    try:
        # Query protocols supported by all public services
        protocols = db.query(Service.protocol).filter(
            Service.is_active == True,
            Service.is_public == True,
            Service.protocol.isnot(None)
        ).distinct().all()
        
        protocol_list = [proto[0] for proto in protocols if proto[0]]
        protocol_list.sort()
        
        logger.info(f"Returning {len(protocol_list)} protocols")
        return protocol_list
        
    except Exception as e:
        logger.error(f"Get protocols failed: {e}")
        raise HTTPException(500, f"Get protocols failed: {str(e)}")


@router.get("/featured")
async def get_featured_services(
    limit: int = Query(6, ge=1, le=20),
    return_tool_format: bool = Query(True),
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get featured services"""
    logger.info(f"Client user {current_user.id} gets featured services")
    
    try:
        # Simple featured: public services with tags
        services = db.query(Service).filter(
            Service.is_active == True,
            Service.is_public == True,
            Service.tags.isnot(None)
        ).options(joinedload(Service.organization)).limit(limit).all()
        
        # Convert to client format
        if return_tool_format:
            results = []
            for service in services:
                org_name = service.organization.name if service.organization else "Unknown"
                tool = service_to_tool_format_safe(service, org_name)
                results.append(tool)
        else:
            results = []
            for service in services:
                org_name = service.organization.name if service.organization else "Unknown"
                service_dict = service_to_client_format(service, org_name)
                results.append(service_dict)
        
        logger.info(f"Returning {len(results)} featured services")
        return results
        
    except Exception as e:
        logger.error(f"Get featured services failed: {e}")
        raise HTTPException(500, f"Get featured services failed: {str(e)}")


@router.get("/stats")
async def get_discovery_stats(
    current_user: User = Depends(get_current_client_user),
    db: Session = Depends(get_db)
):
    """Get discovery statistics"""
    try:
        # Count public services
        total_services = db.query(Service).filter(
            Service.is_active == True,
            Service.is_public == True
        ).count()
        
        # Count categories
        category_count = db.query(Service.category).filter(
            Service.is_active == True,
            Service.is_public == True,
            Service.category.isnot(None)
        ).distinct().count()
        
        # Count organizations
        org_count = db.query(Organization).join(Service).filter(
            Service.is_active == True,
            Service.is_public == True
        ).distinct().count()
        
        return {
            "total_services": total_services,
            "total_categories": category_count,
            "total_organizations": org_count
        }
        
    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        raise HTTPException(500, f"Get stats failed: {str(e)}")

