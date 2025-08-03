from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.posts.models import Post
from src.posts.schemas import PostCreate, PostUpdate, PostResponse
from src.auth.models import User
from src.posts.exceptions import (
    PostNotFoundException,
    InsufficientPermissionsException,
    PostValidationException
)
from src.pagination import PaginationParams

class PostService:
    @staticmethod
    async def create_post(post_data: PostCreate, current_user: User, db: Session) -> Post:
        """Create a new post"""
        db_post = Post(
            title=post_data.title,
            content=post_data.content,
            is_published=post_data.is_published,
            author_id=current_user.id
        )
        
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
        return db_post

    @staticmethod
    async def get_posts(pagination: PaginationParams, db: Session) -> List[Post]:
        """Get all published posts with pagination"""
        query = db.query(Post).filter(Post.is_published == True)
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        posts = query.order_by(desc(Post.created_at)).offset(offset).limit(pagination.size).all()
        
        return posts

    @staticmethod
    async def get_post_by_id(post_id: int, db: Session) -> Post:
        """Get a specific post by ID"""
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise PostNotFoundException()
        return post

    @staticmethod
    async def get_published_post_by_id(post_id: int, db: Session) -> Post:
        """Get a published post by ID"""
        post = db.query(Post).filter(
            Post.id == post_id,
            Post.is_published == True
        ).first()
        if not post:
            raise PostNotFoundException()
        return post

    @staticmethod
    async def update_post(
        post_id: int,
        post_data: PostUpdate,
        current_user: User,
        db: Session
    ) -> Post:
        """Update a post"""
        post = await PostService.get_post_by_id(post_id, db)
        
        # Check if user is the author
        if post.author_id != current_user.id:
            raise InsufficientPermissionsException()
        
        # Update fields
        update_data = post_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(post, field, value)
        
        db.commit()
        db.refresh(post)
        return post

    @staticmethod
    async def delete_post(post_id: int, current_user: User, db: Session):
        """Delete a post"""
        post = await PostService.get_post_by_id(post_id, db)
        
        # Check if user is the author
        if post.author_id != current_user.id:
            raise InsufficientPermissionsException()
        
        db.delete(post)
        db.commit()

    @staticmethod
    async def get_posts_by_user(
        user_id: int,
        pagination: PaginationParams,
        db: Session
    ) -> List[Post]:
        """Get all posts by a specific user"""
        query = db.query(Post).filter(
            Post.author_id == user_id,
            Post.is_published == True
        )
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        posts = query.order_by(desc(Post.created_at)).offset(offset).limit(pagination.size).all()
        
        return posts

    @staticmethod
    async def get_total_posts_count(db: Session) -> int:
        """Get total count of published posts"""
        return db.query(Post).filter(Post.is_published == True).count()

    @staticmethod
    async def get_user_posts_count(user_id: int, db: Session) -> int:
        """Get total count of posts by a specific user"""
        return db.query(Post).filter(
            Post.author_id == user_id,
            Post.is_published == True
        ).count() 