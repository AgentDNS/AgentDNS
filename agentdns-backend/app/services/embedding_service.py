import openai
from typing import List, Dict, Any
import json
import logging
import tiktoken
from ..core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding service using custom OpenAI-compatible API"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for embedding service")
        
        # Configure custom OpenAI client
        self.client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=30.0  # 默认30秒超时
        )
        
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.dimension = settings.MILVUS_DIMENSION
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        
        # Initialize tokenizer for token counting
        try:
            # Use generic encoder for custom models
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback to character-based estimation
            self.encoding = None
            logger.warning("Could not load tiktoken encoder, using character-based estimation")
    
    def create_service_embedding(self, service_data: Dict[str, Any]) -> List[float]:
        """
        Create embedding for a service by concatenating fields to text and embedding it
        """
        # 构建服务的文本表示
        text_parts = []
        
        # Service name (higher weight)
        if service_data.get('name'):
            text_parts.append(f"Service: {service_data['name']}")
        
        # Service category
        if service_data.get('category'):
            text_parts.append(f"Category: {service_data['category']}")
        
        # Basic description
        if service_data.get('description'):
            text_parts.append(f"Description: {service_data['description']}")
        
        # Input and output description
        if service_data.get('input_description'):
            text_parts.append(f"Input: {service_data['input_description']}")
        
        if service_data.get('output_description'):
            text_parts.append(f"Output: {service_data['output_description']}")
        
        # Tags
        if service_data.get('tags'):
            tags_str = ", ".join(service_data['tags'])
            text_parts.append(f"Tags: {tags_str}")
        
        # Protocol
        if service_data.get('protocol'):
            text_parts.append(f"Protocol: {service_data['protocol']}")
        
        # HTTP mode (when using HTTP protocol)
        if service_data.get('http_mode'):
            text_parts.append(f"HTTP Mode: {service_data['http_mode']}")
        
        # Capabilities
        if service_data.get('capabilities'):
            capabilities_str = json.dumps(service_data['capabilities'], ensure_ascii=False)
            text_parts.append(f"Capabilities: {capabilities_str}")
        
        # Organization info
        if service_data.get('organization_name'):
            text_parts.append(f"Organization: {service_data['organization_name']}")
        
        # Join text parts
        full_text = " | ".join(text_parts)
        
        # Truncate to fit API limits
        truncated_text = self._truncate_text(full_text)
        
        # Create embedding via custom API
        embedding = self._get_embedding(truncated_text)
        
        return embedding
    
    def create_query_embedding(self, query: str) -> List[float]:
        """
        Create embedding for search query
        """
        # Preprocess query
        processed_query = self._preprocess_query(query)
        
        # Truncate to fit API limits
        truncated_query = self._truncate_text(processed_query)
        
        # Create embedding via custom API
        embedding = self._get_embedding(truncated_query)
        
        return embedding
    
    def _get_embedding(self, text: str, retries: int = 3) -> List[float]:
        """
        Call custom OpenAI-compatible API to get embedding
        """
        import time
        for attempt in range(retries):
            try:
                # Set a shorter timeout to avoid long hang
                self.client.timeout = 30.0  # 30s timeout
                
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                
                embedding = response.data[0].embedding
                
                # Validate vector dimension
                if len(embedding) != self.dimension:
                    logger.warning(
                        f"Expected dimension {self.dimension}, got {len(embedding)}"
                    )
                
                logger.debug(f"Generated embedding for text: {text[:100]}...")
                return embedding
                
            except Exception as e:
                logger.error(f"Custom OpenAI API error (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    # Retry after short delay
                    time.sleep(1)
                else:
                    # Give up and raise
                    logger.error(f"Failed to get embedding after {retries} attempts: {e}")
                    raise Exception("Embedding service temporarily unavailable, please try again later")
        
        return []
    
    def _truncate_text(self, text: str) -> str:
        """
        Truncate text to fit API token limits
        """
        if self.encoding:
            # Use tiktoken to count tokens
            tokens = self.encoding.encode(text)
            
            if len(tokens) <= self.max_tokens:
                return text
            
            # Truncate tokens and decode back to text
            truncated_tokens = tokens[:self.max_tokens]
            truncated_text = self.encoding.decode(truncated_tokens)
            
            logger.info(f"Text truncated from {len(tokens)} to {len(truncated_tokens)} tokens")
            return truncated_text
        else:
            # Estimate by character length (~1 token ≈ 4 chars)
            estimated_tokens = len(text) // 4
            max_chars = self.max_tokens * 4
            
            if estimated_tokens <= self.max_tokens:
                return text
            
            truncated_text = text[:max_chars]
            logger.info(f"Text truncated from ~{estimated_tokens} to ~{self.max_tokens} tokens (estimated)")
            return truncated_text
    
    def _preprocess_query(self, query: str) -> str:
        """
        Preprocess search query
        """
        # Add common synonyms expansion
        synonyms_map = {
            "ai": "artificial intelligence machine learning",
            "nlp": "natural language processing text analysis",
            "ml": "machine learning artificial intelligence",
            "api": "application programming interface service",
            "chat": "conversation dialogue chatbot",
            "image": "picture photo visual computer vision",
            "translate": "translation language conversion",
            "summarize": "summary abstract summarization",
            "analyze": "analysis analytics examination"
        }
        
        expanded_query = query.lower()
        for term, expansion in synonyms_map.items():
            if term in expanded_query:
                expanded_query += f" {expansion}"
        
        return expanded_query
    
    def batch_create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Batch create embeddings
        """
        embeddings = []
        
        # 截断所有文本
        truncated_texts = [self._truncate_text(text) for text in texts]
        
        try:
            # Set timeout (longer for batch)
            self.client.timeout = 60.0
            
            # Custom API supports batch
            response = self.client.embeddings.create(
                model=self.model,
                input=truncated_texts
            )
            
            for data in response.data:
                embeddings.append(data.embedding)
            
            logger.info(f"Generated {len(embeddings)} embeddings in batch")
            return embeddings
            
        except Exception as e:
            logger.error(f"Batch embedding error: {e}")
            # Fallback to single processing
            for text in truncated_texts:
                try:
                    embedding = self._get_embedding(text)
                    embeddings.append(embedding)
                except Exception as single_error:
                    logger.error(f"Failed to get embedding for text: {single_error}")
                    # Add zero vector as placeholder
                    embeddings.append([0.0] * self.dimension)
            
            return embeddings
    
    def get_token_count(self, text: str) -> int:
        """
        Get token count of text
        """
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Rough estimate: 1 token ≈ 4 characters
            return len(text) // 4
    
    def estimate_cost(self, text: str) -> float:
        """
        Estimate embedding API call cost (USD)
        Note: pricing varies; this uses a generic estimate
        """
        token_count = self.get_token_count(text)
        # 使用通用估算，实际成本请参考具体API提供商定价
        cost_per_1k_tokens = 0.0001  # 可根据实际API定价调整
        return (token_count / 1000) * cost_per_1k_tokens 