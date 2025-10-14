from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.user import User
from ..models.organization import Organization
from ..schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    Organization as OrganizationSchema
)
from .deps import get_current_active_user

router = APIRouter()


@router.post("/", response_model=OrganizationSchema)
def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create organization"""
    # Check if name exists
    if db.query(Organization).filter(Organization.name == org_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name already exists"
        )
    
    # Check if domain exists
    if org_data.domain and db.query(Organization).filter(Organization.domain == org_data.domain).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain is already used by another organization"
        )
    
    # Create organization
    db_org = Organization(
        name=org_data.name,
        domain=org_data.domain,
        display_name=org_data.display_name,
        description=org_data.description,
        website=org_data.website,
        logo_url=org_data.logo_url,
        owner_id=current_user.id
    )
    
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    
    return db_org


@router.get("/", response_model=List[OrganizationSchema])
def list_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List organizations"""
    # Return user's orgs and public verified orgs
    user_orgs = db.query(Organization).filter(
        Organization.owner_id == current_user.id
    )
    
    public_orgs = db.query(Organization).filter(
        Organization.is_verified == True
    )
    
    # Merge results
    all_orgs = user_orgs.union(public_orgs).offset(skip).limit(limit).all()
    
    return all_orgs


@router.get("/my", response_model=List[OrganizationSchema])
def get_my_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's organizations"""
    organizations = db.query(Organization).filter(
        Organization.owner_id == current_user.id
    ).all()
    
    return organizations


@router.get("/{organization_id}", response_model=OrganizationSchema)
def get_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get organization details"""
    organization = db.query(Organization).filter(
        Organization.id == organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check access permission
    if not organization.is_verified and organization.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to access"
        )
    
    return organization


@router.put("/{organization_id}", response_model=OrganizationSchema)
def update_organization(
    organization_id: int,
    org_data: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update organization"""
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.owner_id == current_user.id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or no permission"
        )
    
    # Check if name used by other org
    if org_data.name and org_data.name != organization.name:
        existing = db.query(Organization).filter(
            Organization.name == org_data.name,
            Organization.id != organization_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name already exists"
            )
    
    # Check if domain used by other org
    if org_data.domain and org_data.domain != organization.domain:
        existing = db.query(Organization).filter(
            Organization.domain == org_data.domain,
            Organization.id != organization_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain is already used by another organization"
            )
    
    # Apply updates
    update_data = org_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)
    
    db.commit()
    db.refresh(organization)
    
    return organization


@router.delete("/{organization_id}")
def delete_organization(
    organization_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete organization"""
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.owner_id == current_user.id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or no permission"
        )
    
    # Check whether there are related services (including inactive)
    from ..models.service import Service
    services = db.query(Service).filter(
        Service.organization_id == organization_id
    ).all()
    
    if services:
        # Delete related services (including inactive)
        for service in services:
            # Delete vector from Milvus
            try:
                from ..services.milvus_service import get_milvus_service
                milvus_service = get_milvus_service()
                milvus_service.delete_service_vector(service.id)
            except Exception as e:
                print(f"Warning: Failed to delete vector for service {service.id}: {e}")
            
            # Delete service record
            db.delete(service)
    
    # Delete organization
    db.delete(organization)
    db.commit()
    
    return {"message": "Organization deleted"}