from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional

from agent_dns.api.router import AgentDNSRouter
from agent_dns.db.storage import Storage
from agent_dns.core.resolver import AgentResolver
from agent_dns.models.agent import Agent, Organization, AgentQuery
from agent_dns.db.milvus import AgentDNSDB

# API版本
API_VERSION = "v1"

class AgentDNSServer:
    """AgentDNS API Component Provider"""
    
    def __init__(self, db_url: Optional[str] = None, milvus_db: Optional[AgentDNSDB] = None):
        """
        Initializes the components for AgentDNS.
        
        Args:
            db_url: Database connection URL for SQL.
            milvus_db: Instance of AgentDNSDB for vector search.
        """
        self.storage = Storage(db_url=db_url)
        
        if milvus_db is None:
            # Default MilvusDB initialization if not provided.
            # This might need configuration (e.g., URI, token from env vars)
            # For now, let's assume it can be default-initialized or an error should be raised.
            # Consider making milvus_db a required parameter if no sensible default.
            # For this exercise, let's assume a default init is possible for AgentDNSDB
            # Or, better, ensure main.py ALWAYS provides it.
            # For now, I'll proceed as if main.py will provide it.
            # If milvus_db is essential, an error should be raised if None.
            pass # Assuming milvus_db will be provided by main.py

        self.resolver = AgentResolver(storage=self.storage, milvus_db=milvus_db)
        
        # AgentDNSRouter now takes storage and resolver
        self.router_component = AgentDNSRouter(storage=self.storage, resolver=self.resolver)
        self.router = self.router_component.router # This is the APIRouter instance for main.py
    
    # The run method and create_app might need adjustments if AgentDNSServer no longer manages the FastAPI app directly.
    # For the purpose of this task (making search work), focusing on __init__ and router provision.
    # If main.py handles app creation and running, these might become utility functions or be removed/refactored.

def create_app(db_url: str = None, milvus_db: Optional[AgentDNSDB] = None) -> FastAPI:
    """Creates a FastAPI application instance with AgentDNS routes."""
    
    # This function would now be the primary way to get a configured FastAPI app
    # if main.py wasn't doing its own app setup.
    # If main.py IS doing its own app setup, this function might be redundant
    # or needs to be the one main.py calls.

    app = FastAPI(
            title="AgentDNS",
            description="Agent发现与通信DNS服务",
        version="0.1.0" # Consider moving version to a central place
        )
        
    # Configure CORS
    app.add_middleware(
            CORSMiddleware,
        allow_origins=["*"], # Adjust for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
    server_components = AgentDNSServer(db_url=db_url, milvus_db=milvus_db)
    app.include_router(server_components.router, prefix=f"/api/{API_VERSION}")
        
    # Add health check or other app-level routes here if needed
    @app.get("/")
    async def root():
        return {
            "name": "AgentDNS",
            "description": "Agent发现与通信DNS服务",
            "version": "0.1.0",
            "documentation": "/docs"
        }
    return app

# The if __name__ == "__main__": part would use create_app:
# if __name__ == "__main__":
#     # Предположим, что main.py будет обрабатывать получение URL-адреса БД и инициализацию MilvusDB.
#     # milvus_instance = AgentDNSDB() # Needs proper config
#     # app = create_app(db_url=os.getenv("DB_URL"), milvus_db=milvus_instance)
#     # uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))
# This direct run part of server.py is likely superseded by main.py's uvicorn run.
# For now, I will comment out the direct run part in server.py if main.py is the entry point.
# I will provide the __init__ and relevant parts, and let the existing create_app and run be,
# as they might be used in other contexts or tests. 