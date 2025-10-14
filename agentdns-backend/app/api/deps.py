from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..database import get_db
from ..core.security import verify_token
from ..models.user import User
from ..models.agent import Agent

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user (supports JWT token and Agent API key)"""
    token = credentials.credentials
    
    # If Agent API Key (starts with agent_)
    if token.startswith("agent_"):
        agent = db.query(Agent).filter(Agent.api_key == token).first()
        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Agent API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not agent.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent has been disabled"
            )
        
        if agent.is_suspended:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent has been suspended due to cost limit exceeded"
            )
        
        # Fetch user associated with Agent
        user = db.query(User).filter(User.id == agent.user_id).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with Agent does not exist or has been disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    
    # Otherwise treat as JWT token
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_identifier = payload.get("sub")
    if user_identifier is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Support lookup by user ID or username
    if isinstance(user_identifier, str) and not user_identifier.isdigit():
        # If string and not numeric, treat as username
        user = db.query(User).filter(User.username == user_identifier).first()
    else:
        # Otherwise treat as user ID
        user = db.query(User).filter(User.id == int(user_identifier)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not exist",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account has been disabled"
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user"""
    return current_user 


def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Agent:
    """Get current Agent (Agent API key only)"""
    token = credentials.credentials
    
    if not token.startswith("agent_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This endpoint supports Agent API key only",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    agent = db.query(Agent).filter(Agent.api_key == token).first()
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Agent API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent has been disabled"
        )
    
    if agent.is_suspended:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent has been suspended due to cost limit exceeded"
        )
    
    return agent


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current admin user"""
    from ..core.permissions import PermissionChecker
    PermissionChecker.check_admin_access(current_user)
    return current_user


def get_current_client_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current client user"""
    from ..core.permissions import PermissionChecker
    PermissionChecker.check_client_access(current_user)
    return current_user 