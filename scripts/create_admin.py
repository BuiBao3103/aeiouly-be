#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to create admin user if it doesn't exist
"""
import sys
import os
import codecs

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models first to register them with SQLAlchemy
import src.models  # This will register all models

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.users.models import User, UserRole
from src.config import get_database_url


def create_admin_user():
    """Create admin user if it doesn't exist"""
    
    try:
        # Get database URL
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with Session(engine) as session:
            # Check if admin user already exists
            existing_admin = session.query(User).filter(
                User.username == "admin",
                User.deleted_at.is_(None)
            ).first()
            
            if existing_admin:
                print(f"ℹ️  Admin user already exists with ID {existing_admin.id}")
                print(f"   Email: {existing_admin.email}")
                print(f"   Role: {existing_admin.role.value}")
                return
            
            # Create admin credentials
            admin_data = {
                "email": "admin@aeiouly.com",
                "username": "admin",
                "full_name": "Admin User",
                "password": "admin123",
                "role": UserRole.ADMIN
            }
            
            # Hash password using bcrypt directly
            import bcrypt
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(admin_data["password"].encode('utf-8'), salt).decode('utf-8')
            
            # Create user
            admin_user = User(
                email=admin_data["email"],
                username=admin_data["username"],
                full_name=admin_data["full_name"],
                hashed_password=hashed_password,
                role=admin_data["role"],
                is_active=True
            )
            
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            
            print("✅ Admin user created successfully!")
            print(f"   ID: {admin_user.id}")
            print(f"   Email: {admin_user.email}")
            print(f"   Username: {admin_user.username}")
            print("   Password: admin123")
            print(f"   Role: {admin_user.role.value}")
            
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_admin_user()
