from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class ServiceBase(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0.0"
    is_public: bool = True


class ServiceCreate(ServiceBase):
    endpoint_url: str
    protocol: str = "MCP"  # protocol type: "MCP", "A2A", "ANP", "HTTP"
    authentication_required: bool = True
    pricing_model: str = "per_request"
    price_per_unit: float = 0.0
    currency: str = "CNY"
    tags: Optional[List[str]] = []
    capabilities: Optional[Dict[str, Any]] = {}
    
    # HTTP Agent specific fields
    agentdns_path: Optional[str] = None  # custom agentdns path
    http_method: Optional[str] = None  # HTTP method
    http_mode: Optional[str] = None  # HTTP mode: "sync", "stream", "async"
    input_description: Optional[str] = None  # service input description
    output_description: Optional[str] = None  # service output description
    service_api_key: Optional[str] = None  # provider API key


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    endpoint_url: Optional[str] = None
    protocol: Optional[str] = None  # protocol type: "MCP", "A2A", "ANP", "HTTP"
    authentication_required: Optional[bool] = None
    pricing_model: Optional[str] = None
    price_per_unit: Optional[float] = None
    tags: Optional[List[str]] = None
    capabilities: Optional[Dict[str, Any]] = None
    
    # HTTP Agent specific fields
    agentdns_path: Optional[str] = None
    http_method: Optional[str] = None
    http_mode: Optional[str] = None  # HTTP mode: "sync", "stream", "async"
    input_description: Optional[str] = None
    output_description: Optional[str] = None
    service_api_key: Optional[str] = None


class Service(ServiceBase):
    id: int
    agentdns_uri: str
    is_active: bool
    protocol: str  # protocol type: "MCP", "A2A", "ANP", "HTTP"
    authentication_required: bool
    pricing_model: str
    price_per_unit: float
    currency: str
    tags: List[str]
    capabilities: Dict[str, Any]
    organization_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # HTTP Agent fields
    agentdns_path: Optional[str] = None
    http_method: Optional[str] = None
    http_mode: Optional[str] = None  # HTTP mode: "sync", "stream", "async"
    input_description: Optional[str] = None
    output_description: Optional[str] = None
    
    # Sensitive fields (included only when permitted)
    endpoint_url: Optional[str] = None
    service_api_key: Optional[str] = None
    
    class Config:
        from_attributes = True


class ServiceSearch(BaseModel):
    query: str
    category: Optional[str] = None
    organization: Optional[str] = None
    protocol: Optional[str] = None  # single protocol filter
    max_price: Optional[float] = None
    limit: int = 10


class ServiceDiscovery(BaseModel):
    services: List[Dict[str, Any]]  # services returned by search engine
    total: int
    query: str


# SDK-compliant Tool object structures
class ToolCost(BaseModel):
    """Tool cost information"""
    type: str  # per_request, per_token, per_mb, etc.
    price: str  # price in string
    currency: str = "CNY"
    description: str = "Billed per request"


class Tool(BaseModel):
    """AgentDNS SDK-compliant Tool object"""
    name: str
    description: str
    organization: str  # organization name, not ID
    agentdns_url: str  # agentdns://org/category/service
    cost: ToolCost
    protocol: str = "MCP"  # protocol type: "MCP", "A2A", "ANP", "HTTP"
    method: str = "POST"
    http_mode: Optional[str] = None  # HTTP mode: "sync", "stream", "async"
    input_description: str
    output_description: str


class ToolsListResponse(BaseModel):
    """SDK-compliant tools_list response"""
    tools: List[Tool]
    total: int
    query: str


# Internal full service info (includes sensitive fields)
class ServiceInternal(Service):
    """Internal service model with sensitive fields (not exposed)"""
    endpoint_url: str
    service_api_key_encrypted: Optional[str] = Field(alias="service_api_key")
    
    class Config:
        from_attributes = True


# Keep HttpAgentServiceInfo for future use
class HttpAgentServiceInfo(BaseModel):
    """HTTP Agent discovery response format"""
    name: str
    description: Optional[str] = None
    organization: str
    agentdns: str  # agentdns path
    method: str
    input_description: Optional[str] = None
    output_description: Optional[str] = None 