#!/usr/bin/env python3
"""
Create admin test account script
Used to quickly create an admin account for testing and development

Account info:
- Username: admin
- Password: agentdns_666
- Role: admin
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_admin_user():
    """Create admin user"""
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            logger.warning("⚠️  Admin account already exists")
            logger.info(f"   Username: {existing_user.username}")
            logger.info(f"   Email: {existing_user.email}")
            logger.info(f"   Role: {existing_user.role}")
            logger.info(f"   Status: {'active' if existing_user.is_active else 'inactive'}")
            
            # Ask if reset password
            response = input("\nReset password to 'agentdns_666'? (yes/no): ")
            if response.lower() == 'yes':
                existing_user.hashed_password = get_password_hash("agentdns_666")
                existing_user.is_active = True
                existing_user.is_verified = True
                db.commit()
                logger.info("✅ Password reset")
            else:
                logger.info("❌ Operation cancelled")
            return
        
        # Create new admin user
        admin_user = User(
            username="admin",
            email="admin@agentdns.local",
            hashed_password=get_password_hash("agentdns_666"),
            role="admin",
            is_active=True,
            is_verified=True,
            balance=10000.0  # initial balance
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        logger.info("=" * 50)
        logger.info("✅ Admin account created successfully!")
        logger.info("=" * 50)
        logger.info(f"   Username: admin")
        logger.info(f"   Password: agentdns_666")
        logger.info(f"   Email: {admin_user.email}")
        logger.info(f"   Role: {admin_user.role}")
        logger.info(f"   Balance: ¥{admin_user.balance}")
        logger.info("=" * 50)
        logger.info("")
        logger.info("🚀 You can now use this account to sign in")
        logger.info("📍 Sign-in URL: http://localhost:8000/docs")
        logger.info("")
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"❌ Creation failed: database integrity error - {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Creation failed: {e}")
        raise
    finally:
        db.close()


def main():
    """Main"""
    print("\n🔑 AgentDNS Admin Account Creation Tool")
    print("=" * 50)
    print("")
    
    try:
        create_admin_user()
    except Exception as e:
        logger.error(f"❌ Error during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

