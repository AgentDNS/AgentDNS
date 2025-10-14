from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings
from .database import engine, Base
from .api import auth, services, discovery, agents
from .api.organizations import router as organizations_router
from .api.proxy import router as proxy_router
from .api.billing import router as billing_router

# Import client API routes
from .api.client import auth as client_auth
from .api.client import discovery as client_discovery
from .api.client import services as client_services
from .api.client import account as client_account

# Import client dashboard API routes
from .api.client import dashboard as client_dashboard
from .api.client import api_keys as client_api_keys
from .api.client import billing as client_billing
from .api.client import logs as client_logs
from .api.client import profile as client_profile
from .api.client import user_services as client_user_services
from .api.client import notifications as client_notifications

# Import public API routes
from .api import public as public_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Create database tables on startup
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup on shutdown


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AgentDNS - A root-domain naming and service discovery system designed for LLM Agents",
    lifespan=lifespan,
    redirect_slashes=False  # disable auto slash redirection
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Auth"]
)

app.include_router(
    organizations_router,
    prefix=f"{settings.API_V1_STR}/organizations",
    tags=["Organization Management"]
)

app.include_router(
    services.router,
    prefix=f"{settings.API_V1_STR}/services",
    tags=["Service Management"]
)

app.include_router(
    agents.router,
    prefix=f"{settings.API_V1_STR}/agents",
    tags=["Agent Management"],
    responses={404: {"description": "Not found"}}
)

app.include_router(
    discovery.router,
    prefix=f"{settings.API_V1_STR}/discovery",
    tags=["Service Discovery"]
)

app.include_router(
    proxy_router,
    prefix=f"{settings.API_V1_STR}/proxy",
    tags=["Service Proxy"]
)

app.include_router(
    billing_router,
    prefix=f"{settings.API_V1_STR}/billing",
    tags=["Billing Management"]
)

# === Client API routes ===
app.include_router(
    client_auth.router,
    prefix=f"{settings.API_V1_STR}/client/auth",
    tags=["Client - Auth"]
)

app.include_router(
    client_discovery.router,
    prefix=f"{settings.API_V1_STR}/client/discovery",
    tags=["Client - Discovery"]
)

app.include_router(
    client_services.router,
    prefix=f"{settings.API_V1_STR}/client/services",
    tags=["Client - Service Invocation"]
)

app.include_router(
    client_account.router,
    prefix=f"{settings.API_V1_STR}/client/account",
    tags=["Client - Account Management"]
)

# === Client dashboard API routes ===
app.include_router(
    client_dashboard.router,
    prefix=f"{settings.API_V1_STR}/client/dashboard",
    tags=["Client - Dashboard Overview"]
)

app.include_router(
    client_api_keys.router,
    prefix=f"{settings.API_V1_STR}/client/api-keys",
    tags=["Client - API Key Management"]
)

app.include_router(
    client_billing.router,
    prefix=f"{settings.API_V1_STR}/client/billing",
    tags=["Client - Billing Management"]
)

app.include_router(
    client_logs.router,
    prefix=f"{settings.API_V1_STR}/client/logs",
    tags=["Client - Usage Logs"]
)

app.include_router(
    client_profile.router,
    prefix=f"{settings.API_V1_STR}/client/profile",
    tags=["Client - User Profile"]
)

app.include_router(
    client_user_services.router,
    prefix=f"{settings.API_V1_STR}/client/user-services",
    tags=["Client - User Services"]
)

app.include_router(
    client_notifications.router,
    prefix=f"{settings.API_V1_STR}/client/notifications",
    tags=["Client - Notifications"]
)

# === Public API routes (no auth required) ===
app.include_router(
    public_api.router,
    prefix=f"{settings.API_V1_STR}/public",
    tags=["Public"]
)


@app.get("/")
async def root():
    """Root path"""
    return {
        "message": "Welcome to the AgentDNS API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "AgentDNS API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 