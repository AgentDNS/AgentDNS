from pymilvus import connections, Collection, CollectionSchema, DataType, FieldSchema, utility
from typing import List, Dict, Any, Tuple
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)


class MilvusService:
    """Milvus vector database service"""
    
    def __init__(self):
        self.collection_name = settings.MILVUS_COLLECTION_NAME
        self.dimension = settings.MILVUS_DIMENSION
        self.collection = None
        self._init_connection()
        self._init_collection()
    
    def _init_connection(self):
        """Initialize Milvus connection"""
        try:
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT
            )
            logger.info(f"Connected to Milvus at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise
    
    def _init_collection(self):
        """Initialize collection"""
        try:
            # 检查集合是否存在
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Collection {self.collection_name} already exists")
            else:
                # 创建新集合
                self._create_collection()
            
            # 加载集合到内存
            self.collection.load()
            
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise
    
    def _create_collection(self):
        """Create new collection"""
        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="service_id", dtype=DataType.INT64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="service_name", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="organization_id", dtype=DataType.INT64),
        ]
        
        # 创建集合schema
        schema = CollectionSchema(
            fields=fields,
            description="AgentDNS services vector collection"
        )
        
        # 创建集合
        self.collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # 创建索引
        index_params = {
            "metric_type": "COSINE",  # cosine similarity
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        
        logger.info(f"Created new collection {self.collection_name}")
    
    def insert_service_vector(
        self,
        service_id: int,
        embedding: List[float],
        service_name: str,
        category: str,
        organization_id: int
    ) -> bool:
        """Insert service vector into Milvus"""
        try:
            # 准备数据
            entities = [
                [service_id],  # service_id
                [embedding],   # embedding
                [service_name], # service_name
                [category or ""], # category
                [organization_id] # organization_id
            ]
            
            # 插入数据
            insert_result = self.collection.insert(entities)
            
            # 刷新以确保数据被持久化
            self.collection.flush()
            
            logger.info(f"Inserted vector for service {service_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert vector for service {service_id}: {e}")
            return False
    
    def search_similar_services(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        category_filter: str = None,
        organization_filter: int = None
    ) -> List[Dict[str, Any]]:
        """Search similar services"""
        try:
            # Build search params
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # Build filter expression
            expr_parts = []
            if category_filter:
                expr_parts.append(f'category == "{category_filter}"')
            if organization_filter:
                expr_parts.append(f'organization_id == {organization_filter}')
            
            expr = " && ".join(expr_parts) if expr_parts else None
            
            # Execute search
            search_results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["service_id", "service_name", "category", "organization_id"]
            )
            
            # Process results
            results = []
            for hits in search_results:
                for hit in hits:
                    results.append({
                        "service_id": hit.entity.get("service_id"),
                        "service_name": hit.entity.get("service_name"),
                        "category": hit.entity.get("category"),
                        "organization_id": hit.entity.get("organization_id"),
                        "similarity": float(hit.score)
                    })
            
            logger.info(f"Found {len(results)} similar services")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar services: {e}")
            return []
    
    def update_service_vector(
        self,
        service_id: int,
        embedding: List[float],
        service_name: str,
        category: str,
        organization_id: int
    ) -> bool:
        """Update service vector"""
        try:
            # 首先删除旧的向量（忽略结果，因为可能没有旧向量）
            try:
                self.delete_service_vector(service_id)
                logger.debug(f"Deleted existing vectors for service {service_id}")
            except Exception as delete_error:
                logger.warning(f"Error deleting existing vectors for service {service_id}: {delete_error}")
                # Continue; deletion failure shouldn't block update
            
            # 插入新的向量
            return self.insert_service_vector(
                service_id, embedding, service_name, category, organization_id
            )
            
        except Exception as e:
            logger.error(f"Failed to update vector for service {service_id}: {e}")
            return False
    
    def delete_service_vector(self, service_id: int) -> bool:
        """Delete service vector"""
        try:
            # Delete vectors for given service_id
            expr = f"service_id == {service_id}"
            delete_result = self.collection.delete(expr)
            
            # Flush to ensure persistence
            self.collection.flush()
            
            logger.info(f"Deleted vector for service {service_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vector for service {service_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            # Use Milvus API to get stats
            self.collection.load()
            
            # Get num entities
            num_entities = self.collection.num_entities
            
            return {
                "num_entities": num_entities,
                "collection_name": self.collection_name
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"num_entities": 0, "collection_name": self.collection_name}


# Global Milvus service instance
milvus_service = None


def get_milvus_service() -> MilvusService:
    """Get Milvus service instance"""
    global milvus_service
    if milvus_service is None:
        milvus_service = MilvusService()
    return milvus_service 