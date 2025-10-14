import re
import json
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, Text
import logging

from ..models.service import Service, ServiceMetadata
from ..models.organization import Organization
from .embedding_service import EmbeddingService
from .milvus_service import get_milvus_service

logger = logging.getLogger(__name__)


def service_to_safe_dict(service: Service) -> dict:
    """Convert Service to a safe dict (exclude sensitive fields, include HTTP Agent fields)"""
    return {
        "id": service.id,
        "name": service.name,
        "category": service.category,
        "agentdns_uri": service.agentdns_uri,
        "description": service.description,
        "version": service.version,
        "is_active": service.is_active,
        "is_public": service.is_public,
        # Note: exclude endpoint_url and service_api_key
        "supported_protocols": service.supported_protocols or [],
        "authentication_required": service.authentication_required,
        "pricing_model": service.pricing_model,
        "price_per_unit": service.price_per_unit,
        "currency": service.currency,
        "tags": service.tags or [],
        "capabilities": service.capabilities or {},
        "organization_id": service.organization_id,
        "created_at": service.created_at,
        "updated_at": service.updated_at,
        
        # HTTP Agent服务字段（完整返回，但不包含敏感信息）
        "agentdns_path": service.agentdns_path,
        "http_method": service.http_method,
        "input_description": service.input_description,
        "output_description": service.output_description,
    }


def service_to_tool_format(service: Service) -> dict:
    """Convert Service to SDK-compliant Tool format"""
    
    # Get organization name
    organization_name = "Unknown"
    if hasattr(service, 'organization') and service.organization:
        organization_name = service.organization.name
    
    # Build cost object
    cost_description_map = {
        "per_request": "Billed per request",
        "per_token": "Billed per token", 
        "per_mb": "Billed per MB transferred",
        "monthly": "Billed monthly",
        "yearly": "Billed yearly"
    }
    
    cost = {
        "type": service.pricing_model or "per_request",
        "price": str(service.price_per_unit or 0.0),
        "currency": service.currency or "CNY",
        "description": cost_description_map.get(service.pricing_model, "Billed per request")
    }
    
    return {
        "name": service.name or "",
        "description": service.description or "",
        "organization": organization_name,
        "agentdns_url": service.agentdns_uri or "",
        "cost": cost,
        "protocol": service.protocol or "MCP",
        "method": service.http_method or "POST",
        "http_mode": service.http_mode,  # HTTP mode
        "input_description": service.input_description or "{}",
        "output_description": service.output_description or "{}"
    }


class SearchEngine:
    """AgentDNS service search engine - vector-based"""
    
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.milvus_service = get_milvus_service()
    
    def search(
        self,
        query: str,
        category: Optional[str] = None,
        organization: Optional[str] = None,
        protocol: Optional[str] = None,  # 改为单个协议
        max_price: Optional[float] = None,
        limit: int = 10,
        return_tool_format: bool = False
    ) -> Tuple[List[dict], int]:
        """Execute service search (vector-based), return safe dict list or Tool list"""
        
        logger.info(f"Searching for: '{query}' with filters - category: {category}, organization: {organization}, protocol: {protocol}, max_price: {max_price}")
        
        try:
            # 1) Check Milvus for vectors
            stats = self.milvus_service.get_collection_stats()
            vector_count = stats.get("num_entities", 0)
            logger.info(f"Milvus collection contains {vector_count} vectors")
            
            if vector_count == 0:
                logger.warning("No vectors found in Milvus, returning empty results")
                return [], 0
            
            # 2) Create query embedding
            logger.debug("Generating query embedding...")
            query_embedding = self.embedding_service.create_query_embedding(query)
            
            # 3) Determine organization filter
            organization_id_filter = None
            if organization:
                org = self.db.query(Organization).filter(
                    Organization.name == organization
                ).first()
                if org:
                    organization_id_filter = org.id
                    logger.debug(f"Organization filter: {organization} (ID: {organization_id_filter})")
            
            # 4) Vector search in Milvus
            logger.debug(f"Performing vector search with top_k={limit * 3}")
            vector_results = self.milvus_service.search_similar_services(
                query_embedding=query_embedding,
                top_k=limit * 3,  # 获取更多结果用于后续过滤
                category_filter=category,
                organization_filter=organization_id_filter
            )
            
            logger.info(f"Vector search returned {len(vector_results)} results")
            
            if not vector_results:
                logger.warning("No vector search results found")
                return [], 0
            
            # 5) Fetch full services from DB, preload organization
            service_ids = [result["service_id"] for result in vector_results]
            logger.debug(f"Fetching services for IDs: {service_ids[:5]}...")  # 只记录前5个ID
            
            services_query = self.db.query(Service).filter(
                Service.id.in_(service_ids),
                Service.is_active == True,
                Service.is_public == True
            )
            
            # Preload organization if returning Tool format
            if return_tool_format:
                services_query = services_query.options(joinedload(Service.organization))
            
            # 6) Apply additional filters
            if protocol:
                logger.debug(f"Applying protocol filter: {protocol}")
                services_query = services_query.filter(Service.protocol == protocol)
            
            if max_price is not None:
                logger.debug(f"Applying price filter: <= {max_price}")
                services_query = services_query.filter(Service.price_per_unit <= max_price)
            
            # 7) Get service list
            services_dict = {service.id: service for service in services_query.all()}
            logger.info(f"Found {len(services_dict)} services after database filtering")
            
            # 8) Order by similarity, limit, and convert to desired format
            ordered_services = []
            added_service_ids = set()
            similarity_scores = {}
            
            for result in vector_results:
                service_id = result["service_id"]
                similarity = result["similarity"]
                
                if service_id in services_dict:
                    # Skip duplicates
                    if service_id in added_service_ids:
                        continue

                    service = services_dict[service_id]
                    
                    # 根据参数选择返回格式
                    if return_tool_format:
                        # Convert to Tool format
                        tool_service = service_to_tool_format(service)
                        ordered_services.append(tool_service)
                    else:
                        # Convert to safe dict (HTTP Agent fields, no sensitive info)
                        safe_service = service_to_safe_dict(service)
                        ordered_services.append(safe_service)
                    
                    similarity_scores[service_id] = similarity
                    added_service_ids.add(service_id)
                    
                    logger.debug(f"Service {service.name} (ID: {service_id}) similarity: {similarity:.4f}")
                    
                    if len(ordered_services) >= limit:
                        break
            
            total = len(ordered_services)
            
            logger.info(f"Final search results: {total} services found")
            
            # Log similarity range for debugging
            if similarity_scores:
                max_similarity = max(similarity_scores.values())
                min_similarity = min(similarity_scores.values())
                logger.debug(f"Similarity scores range: {min_similarity:.4f} - {max_similarity:.4f}")
            
            return ordered_services, total
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}", exc_info=True)
            # Vector search failed; return empty
            return [], 0
    
    def get_vector_search_stats(self) -> dict:
        """Get vector search statistics"""
        try:
            stats = self.milvus_service.get_collection_stats()
            return {
                "milvus_enabled": True,
                "total_vectors": stats.get("num_entities", 0),
                "collection_name": stats.get("collection_name", "unknown"),
                "vector_dimension": self.embedding_service.dimension,
                "embedding_model": self.embedding_service.model
            }
        except Exception as e:
            logger.error(f"Error getting vector search stats: {e}")
            return {
                "milvus_enabled": False,
                "error": str(e)
            } 