from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from src.auth.models import User
from src.auth.schemas import UserCreate, Token
from src.auth.exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    UserNotFoundException
)
from src.auth.config import ACCESS_TOKEN_EXPIRE_MINUTES
from src.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    async def register_user(user_data: UserCreate, db: Session) -> User:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()
        
        if existing_user:
            raise UserAlreadyExistsException()

        # Create new user
        hashed_password = AuthService.get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    async def authenticate_user(username: str, password: str, db: Session) -> Token:
        user = db.query(User).filter(User.username == username).first()
        if not user or not AuthService.verify_password(password, user.hashed_password):
            raise InvalidCredentialsException()
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer")

    @staticmethod
    async def get_user_by_id(user_id: int, db: Session) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundException()
        return user

    @staticmethod
    async def get_user_by_username(username: str, db: Session) -> User:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise UserNotFoundException()
        return user 