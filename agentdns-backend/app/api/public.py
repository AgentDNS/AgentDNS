"""
Public APIs - endpoints that do not require authentication
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from ..database import get_db
from ..models.service import Service
from ..models.organization import Organization
from ..core.permissions import service_to_tool_format_safe, service_to_client_format

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/trending")
async def get_public_trending_services(
    limit: int = Query(10, ge=1, le=50),
    return_tool_format: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get trending services - public endpoint, no auth required"""
    logger.info(f"Get public trending services, limit: {limit}")
    
    try:
        # Query public and active services, order by created_at (simple trending)
        services_query = db.query(Service).filter(
            Service.is_public == True,
            Service.is_active == True
        ).order_by(Service.created_at.desc()).limit(limit)
        
        services = services_query.all()
        
        if return_tool_format:
            # Convert to Tool format
            result = []
            for service in services:
                # Get organization name
                organization_name = "Unknown"
                if service.organization_id:
                    organization = db.query(Organization).filter(
                        Organization.id == service.organization_id
                    ).first()
                    if organization:
                        organization_name = organization.name
                
                tool_data = service_to_tool_format_safe(service, organization_name)
                result.append(tool_data)
            
            return result
        else:
            # Convert to client-safe format
            result = []
            for service in services:
                organization_name = "Unknown"
                if service.organization_id:
                    organization = db.query(Organization).filter(
                        Organization.id == service.organization_id
                    ).first()
                    if organization:
                        organization_name = organization.name
                
                client_data = service_to_client_format(service, organization_name)
                result.append(client_data)
            
            return result
            
    except Exception as e:
        logger.error(f"Failed to get public trending services: {str(e)}")
        return []


@router.get("/categories")
async def get_public_service_categories(
    db: Session = Depends(get_db)
):
    """Get service categories - public endpoint"""
    logger.info("Get public service categories")
    
    try:
        # Query categories from public services
        categories = db.query(Service.category).filter(
            Service.is_public == True,
            Service.is_active == True,
            Service.category.isnot(None)
        ).distinct().all()
        
        # Extract category names and filter empty ones
        category_list = [cat[0] for cat in categories if cat[0]]
        
        return sorted(category_list)
        
    except Exception as e:
        logger.error(f"Failed to get public service categories: {str(e)}")
        return []


@router.get("/protocols")
async def get_public_service_protocols(
    db: Session = Depends(get_db)
):
    """Get service protocols - public endpoint"""
    logger.info("Get public service protocols")
    
    try:
        # Query protocols from public services
        protocols = db.query(Service.protocol).filter(
            Service.is_public == True,
            Service.is_active == True,
            Service.protocol.isnot(None)
        ).distinct().all()
        
        # Extract protocol names and filter empty ones
        protocol_list = [proto[0] for proto in protocols if proto[0]]
        
        return sorted(protocol_list)
        
    except Exception as e:
        logger.error(f"Failed to get public service protocols: {str(e)}")
        return []


@router.get("/stats")
async def get_public_stats(
    db: Session = Depends(get_db)
):
    """Get public statistics"""
    logger.info("Get public statistics")
    
    try:
        # Count public services
        total_services = db.query(Service).filter(
            Service.is_public == True,
            Service.is_active == True
        ).count()
        
        # Count categories
        categories_count = db.query(Service.category).filter(
            Service.is_public == True,
            Service.is_active == True,
            Service.category.isnot(None)
        ).distinct().count()
        
        # Count protocols
        protocols_count = db.query(Service.protocol).filter(
            Service.is_public == True,
            Service.is_active == True,
            Service.protocol.isnot(None)
        ).distinct().count()
        
        return {
            "total_services": total_services,
            "categories_count": categories_count,
            "protocols_count": protocols_count
        }
        
    except Exception as e:
        logger.error(f"Failed to get public statistics: {str(e)}")
        return {
            "total_services": 0,
            "categories_count": 0,
            "protocols_count": 0
        }
