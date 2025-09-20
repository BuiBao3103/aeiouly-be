#!/usr/bin/env python3
"""
Script to create an admin user.

Usage:
    python -m scripts.create_admin --username admin --email admin@example.com --password yourpassword
"""
import argparse
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.auth.models import User, UserRole
from src.auth.service import AuthService

def create_admin_user(username: str, email: str, password: str):
    """Create a new admin user."""
    db: Session = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            print(f"Error: User with email {email} or username {username} already exists.")
            return False

        # Create new admin user
        hashed_password = AuthService.get_password_hash(password)
        admin_user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"Admin user '{username}' created successfully with email: {email}")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin user")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    
    args = parser.parse_args()
    
    if len(args.password) < 8:
        print("Error: Password must be at least 8 characters long")
        sys.exit(1)
    
    success = create_admin_user(args.username, args.email, args.password)
    sys.exit(0 if success else 1)
