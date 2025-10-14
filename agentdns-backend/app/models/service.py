from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)  # service name
    category = Column(String(50), index=True)  # service category
    agentdns_uri = Column(String(500), unique=True, index=True, nullable=False)  # agentdns://org/category/name
    description = Column(Text)  # service description (merged short and long)
    version = Column(String(20), default="1.0.0")
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)  # public or not
    
    # Endpoint config
    endpoint_url = Column(String(500), nullable=False)  # actual endpoint
    protocol = Column(String(20), default="MCP")  # protocol: "MCP", "A2A", "ANP", "HTTP"
    authentication_required = Column(Boolean, default=True)
    
    # HTTP Agent specific
    agentdns_path = Column(String(500), index=True)  # custom agentdns path, e.g., org/search/websearch
    http_method = Column(String(10))  # HTTP method: GET, POST, etc.
    http_mode = Column(String(10))  # HTTP mode: "sync", "stream", "async"
    input_description = Column(Text)  # input description
    output_description = Column(Text)  # output description
    service_api_key = Column(String(500))  # provider API key (encrypted)
    
    # Pricing
    pricing_model = Column(String(50))  # "per_request", "per_token", "subscription"
    price_per_unit = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    
    # Metadata
    tags = Column(JSON)  # tags
    capabilities = Column(JSON)  # capabilities description
    
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="services")
    service_metadata = relationship("ServiceMetadata", back_populates="service", uselist=False)
    usage_records = relationship("Usage", back_populates="service")
    async_tasks = relationship("AsyncTask", back_populates="service")


class ServiceMetadata(Base):
    __tablename__ = "service_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    
    # API spec
    openapi_spec = Column(JSON)  # OpenAPI spec
    examples = Column(JSON)  # usage examples
    rate_limits = Column(JSON)  # rate limits
    
    # Runtime info
    health_check_url = Column(String(500))
    status = Column(String(20), default="active")  # active, maintenance, deprecated
    uptime_stats = Column(JSON)  # 可用性统计
    
    # Search optimization
    search_keywords = Column(JSON)  # search keywords
    embedding_vector = Column(JSON)  # embedding vector (semantic search)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    service = relationship("Service", back_populates="service_metadata") 