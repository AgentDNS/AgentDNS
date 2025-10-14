from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import re
import json

from ..database import get_db, get_redis
from ..models.user import User
from ..models.service import Service, ServiceMetadata
from ..models.organization import Organization
from ..schemas.service import (
    ServiceSearch, ServiceDiscovery, Service as ServiceSchema,
    ToolsListResponse, Tool, ToolCost
)
from .deps import get_current_active_user
from ..services.search_engine import SearchEngine, service_to_tool_format
from ..services.embedding_service import EmbeddingService
from ..core.config import settings

router = APIRouter()


@router.post("/search", response_model=ToolsListResponse)
def search_services(
    search_data: ServiceSearch,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Natural language service discovery - returns tools_list per SDK spec"""
    search_engine = SearchEngine(db)
    
    # 执行搜索，返回Tool格式的服务列表
    tools, total = search_engine.search(
        query=search_data.query,
        category=search_data.category,
        organization=search_data.organization,
        protocol=search_data.protocol,  # 改为单个协议
        max_price=search_data.max_price,
        limit=search_data.limit,
        return_tool_format=True  # 启用Tool格式
    )
    
    return ToolsListResponse(
        tools=tools,
        total=total,
        query=search_data.query
    )


@router.get("/resolve/{agentdns_uri:path}", response_model=Tool)
def resolve_service(
    agentdns_uri: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Resolve AgentDNS URI to Tool format"""
    
    # Normalize URI
    if not agentdns_uri.startswith("agentdns://"):
        agentdns_uri = f"agentdns://{agentdns_uri}"
    
    # Find service with organization preloaded
    service = db.query(Service).options(
        joinedload(Service.organization)
    ).filter(
        Service.agentdns_uri == agentdns_uri,
        Service.is_active == True
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or disabled"
        )
    
    # Check access permission
    if not service.is_public:
        organization = service.organization
        if organization and organization.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No permission to access"
            )
    
    # Convert to Tool format
    tool_data = service_to_tool_format(service)
    return Tool(**tool_data)


@router.get("/categories", response_model=List[str])
def get_categories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get available service categories"""
    categories = db.query(Service.category).filter(
        Service.category.isnot(None),
        Service.is_active == True,
        Service.is_public == True
    ).distinct().all()
    
    return [cat[0] for cat in categories if cat[0]]


@router.get("/protocols", response_model=List[str])
def get_protocols(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get supported protocol list"""
    # Extract protocols from all active services
    protocols = db.query(Service.protocol).filter(
        Service.is_active == True,
        Service.is_public == True,
        Service.protocol.isnot(None)
    ).distinct().all()
    
    return sorted([protocol[0] for protocol in protocols if protocol[0]])


@router.get("/trending", response_model=List[Tool])
def get_trending_services(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get trending services (Tool format)"""
    # Simple implementation: order by created_at desc, active & public
    services = db.query(Service).options(
        joinedload(Service.organization)
    ).filter(
        Service.is_active == True,
        Service.is_public == True
    ).order_by(Service.created_at.desc()).limit(limit).all()
    
    tools = []
    for service in services:
        tool_data = service_to_tool_format(service)
        tools.append(Tool(**tool_data))
    
    return tools


@router.get("/vector-stats")
def get_vector_search_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get vector search statistics"""
    search_engine = SearchEngine(db)
    vector_stats = search_engine.get_vector_search_stats()
    
    # Add DB stats
    db_stats = {
        "total_services": db.query(Service).filter(
            Service.is_active == True
        ).count(),
        "public_services": db.query(Service).filter(
            Service.is_active == True,
            Service.is_public == True
        ).count(),
        "http_agent_services": db.query(Service).filter(
            Service.is_active == True,
            Service.is_public == True,
            Service.agentdns_path.isnot(None)
        ).count()
    }
    
    # Add embedding config
    embedding_config = {
        "provider": "OpenAI",
        "model": settings.OPENAI_EMBEDDING_MODEL,
        "dimension": settings.MILVUS_DIMENSION,
        "max_tokens": settings.OPENAI_MAX_TOKENS,
        "api_key_configured": bool(settings.OPENAI_API_KEY)
    }
    
    # If possible, add cost estimate example
    try:
        embedding_service = EmbeddingService()
        sample_text = "This is a sample service for AI-powered text processing"
        cost_estimate = embedding_service.estimate_cost(sample_text)
        token_count = embedding_service.get_token_count(sample_text)
        
        embedding_config.update({
            "cost_per_embedding_example": {
                "text": sample_text,
                "tokens": token_count,
                "estimated_cost_usd": round(cost_estimate, 6)
            }
        })
    except Exception as e:
        embedding_config["error"] = f"Failed to initialize embedding service: {str(e)}"
    
    return {
        "vector_search": vector_stats,
        "database": db_stats,
        "embedding_config": embedding_config
    } 