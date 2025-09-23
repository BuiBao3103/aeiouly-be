"""
Service layer for Posts module with instance methods
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from src.posts.models import Post, PostLike
from src.posts.schemas import PostCreate, PostUpdate, PostResponse
from src.auth.models import User, UserRole
from src.posts.exceptions import (
    PostNotFoundException,
    InsufficientPermissionsException,
    PostValidationException
)
from src.pagination import PaginationParams
from src.storage import S3StorageService
from fastapi import UploadFile, HTTPException


class PostService:
    def __init__(self):
        """Initialize PostService with dependencies"""
        self.storage_service = S3StorageService()
    
    async def create_post(self, post_data: PostCreate, current_user: User, db: Session) -> PostResponse:
        """
        Tạo bài viết mới - Chỉ admin mới có thể tạo bài viết

        Args:
            post_data: Dữ liệu bài viết mới
            current_user: User hiện tại
            db: Database session

        Returns:
            PostResponse: Thông tin bài viết đã tạo
        
        Raises:
            InsufficientPermissionsException: Nếu không phải admin
        """
        # Kiểm tra quyền admin
        if current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException("Chỉ admin mới có thể tạo bài viết")

        try:
            db_post = Post(
                content=post_data.content,
                is_published=post_data.is_published,
                author_id=current_user.id,
            )

            db.add(db_post)
            db.commit()
            db.refresh(db_post)

            # Return post with like information
            return PostResponse(
                id=db_post.id,
                content=db_post.content,
                is_published=db_post.is_published,
                image_url=db_post.image_url,
                author={
                    "id": db_post.author.id,
                    "username": db_post.author.username,
                    "full_name": db_post.author.full_name
                },
                likes_count=0,  # New post has no likes
                is_liked_by_user=False,  # Creator hasn't liked their own post
                created_at=db_post.created_at,
                updated_at=db_post.updated_at
            )
        except Exception as e:
            db.rollback()
            raise PostValidationException(f"Lỗi khi tạo bài viết: {str(e)}")

    async def upload_post_image(
        self,
        post_id: int, 
        image: UploadFile, 
        current_user: User, 
        db: Session
    ) -> PostResponse:
        """
        Upload hình ảnh cho bài viết. Chỉ tác giả hoặc admin được phép.
        """
        # Validate content-type
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File phải là hình ảnh")

        # Check post exists
        post = await self.get_post_by_id(post_id, db)
        if not post:
            raise PostNotFoundException(f"Không tìm thấy bài viết với ID {post_id}")

        # Check permission
        if post.author_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException("Chỉ tác giả hoặc admin mới có thể upload hình ảnh")

        try:
            # Delete old image if exists
            if post.image_url:
                self.storage_service.delete_file(post.image_url)

            # Upload new image to S3
            url = self.storage_service.upload_fileobj(image.file, image.content_type, key_prefix="posts/")

            # Update post with new image URL
            post.image_url = url
            db.commit()
            db.refresh(post)

            # Get like info
            likes_count = await self.get_post_likes_count(post.id, db)
            is_liked = await self.is_post_liked_by_user(post.id, current_user.id, db)

            # Build response
            return PostResponse(
                id=post.id,
                content=post.content,
                is_published=post.is_published,
                image_url=post.image_url,
                author={
                    "id": post.author.id,
                    "username": post.author.username,
                    "full_name": post.author.full_name
                },
                likes_count=likes_count,
                is_liked_by_user=is_liked,
                created_at=post.created_at,
                updated_at=post.updated_at
            )
        except Exception as e:
            db.rollback()
            raise PostValidationException(f"Lỗi khi upload hình ảnh: {str(e)}")

    async def get_posts(self, pagination: PaginationParams, db: Session) -> List[Post]:
        """Get all published posts with pagination"""
        query = db.query(Post).filter(Post.is_published == True)

        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        posts = query.order_by(desc(Post.created_at)).offset(offset).limit(pagination.size).all()

        return posts

    async def get_post_by_id(self, post_id: int, db: Session) -> Post:
        """Get a specific post by ID"""
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise PostNotFoundException(f"Không tìm thấy bài viết với ID {post_id}")
        return post

    async def get_post_by_id_with_like_info(self, post_id: int, current_user: Optional[User], db: Session) -> PostResponse:
        """Get post by ID with like information"""
        post = await self.get_post_by_id(post_id, db)
        
        # Get like information
        likes_count = await self.get_post_likes_count(post.id, db)
        is_liked = False
        if current_user:
            is_liked = await self.is_post_liked_by_user(post.id, current_user.id, db)

        return PostResponse(
            id=post.id,
            content=post.content,
            is_published=post.is_published,
            image_url=post.image_url,
            author={
                "id": post.author.id,
                "username": post.author.username,
                "full_name": post.author.full_name
            },
            likes_count=likes_count,
            is_liked_by_user=is_liked,
            created_at=post.created_at,
            updated_at=post.updated_at
        )

    async def get_posts_with_like_info(self, pagination: PaginationParams, current_user: Optional[User], db: Session) -> List[PostResponse]:
        """Get all published posts with like information"""
        posts = await self.get_posts(pagination, db)
        
        result = []
        for post in posts:
            likes_count = await self.get_post_likes_count(post.id, db)
            is_liked = False
            if current_user:
                is_liked = await self.is_post_liked_by_user(post.id, current_user.id, db)
            
            result.append(PostResponse(
                id=post.id,
                content=post.content,
                is_published=post.is_published,
                image_url=post.image_url,
                author={
                    "id": post.author.id,
                    "username": post.author.username,
                    "full_name": post.author.full_name
                },
                likes_count=likes_count,
                is_liked_by_user=is_liked,
                created_at=post.created_at,
                updated_at=post.updated_at
            ))
        
        return result

    async def get_posts_by_user_with_like_info(self, user_id: int, pagination: PaginationParams, current_user: Optional[User], db: Session) -> List[PostResponse]:
        """Get posts by user with like information"""
        query = db.query(Post).filter(Post.author_id == user_id)
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        posts = query.order_by(desc(Post.created_at)).offset(offset).limit(pagination.size).all()
        
        result = []
        for post in posts:
            likes_count = await self.get_post_likes_count(post.id, db)
            is_liked = False
            if current_user:
                is_liked = await self.is_post_liked_by_user(post.id, current_user.id, db)
            
            result.append(PostResponse(
                id=post.id,
                content=post.content,
                is_published=post.is_published,
                image_url=post.image_url,
                author={
                    "id": post.author.id,
                    "username": post.author.username,
                    "full_name": post.author.full_name
                },
                likes_count=likes_count,
                is_liked_by_user=is_liked,
                created_at=post.created_at,
                updated_at=post.updated_at
            ))
        
        return result

    async def update_post(self, post_id: int, post_data: PostUpdate, current_user: User, db: Session) -> PostResponse:
        """Update a post"""
        post = await self.get_post_by_id(post_id, db)
        
        # Check permission
        if post.author_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException("Chỉ tác giả hoặc admin mới có thể cập nhật bài viết")

        try:
            # Update fields
            if post_data.content is not None:
                post.content = post_data.content
            if post_data.is_published is not None:
                post.is_published = post_data.is_published

            db.commit()
            db.refresh(post)

            # Get like information
            likes_count = await self.get_post_likes_count(post.id, db)
            is_liked = await self.is_post_liked_by_user(post.id, current_user.id, db)

            return PostResponse(
                id=post.id,
                content=post.content,
                is_published=post.is_published,
                image_url=post.image_url,
                author={
                    "id": post.author.id,
                    "username": post.author.username,
                    "full_name": post.author.full_name
                },
                likes_count=likes_count,
                is_liked_by_user=is_liked,
                created_at=post.created_at,
                updated_at=post.updated_at
            )
        except Exception as e:
            db.rollback()
            raise PostValidationException(f"Lỗi khi cập nhật bài viết: {str(e)}")

    async def delete_post(self, post_id: int, current_user: User, db: Session) -> bool:
        """Delete a post"""
        post = await self.get_post_by_id(post_id, db)
        
        # Check permission
        if post.author_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException("Chỉ tác giả hoặc admin mới có thể xóa bài viết")

        try:
            db.delete(post)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise PostValidationException(f"Lỗi khi xóa bài viết: {str(e)}")

    async def like_post(self, post_id: int, current_user: User, db: Session) -> PostResponse:
        """Like or unlike a post"""
        # Check if post exists
        post = await self.get_post_by_id(post_id, db)
        
        # Check if already liked
        existing_like = db.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == current_user.id
        ).first()

        if existing_like:
            # Unlike
            db.delete(existing_like)
            db.commit()
            is_liked = False
        else:
            # Like
            new_like = PostLike(post_id=post_id, user_id=current_user.id)
            db.add(new_like)
            db.commit()
            is_liked = True

        # Get updated likes count
        likes_count = self.get_post_likes_count(post_id, db)

        return PostResponse(
            id=post.id,
            content=post.content,
            is_published=post.is_published,
            image_url=post.image_url,
            author={
                "id": post.author.id,
                "username": post.author.username,
                "full_name": post.author.full_name
            },
            likes_count=likes_count,
            is_liked_by_user=is_liked,
            created_at=post.created_at,
            updated_at=post.updated_at
        )

    async def get_post_likes_count(self, post_id: int, db: Session) -> int:
        """Get likes count for a post"""
        return db.query(PostLike).filter(PostLike.post_id == post_id).count()

    async def is_post_liked_by_user(self, post_id: int, user_id: int, db: Session) -> bool:
        """Check if post is liked by user"""
        like = db.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id
        ).first()
        return like is not None

    async def get_total_posts_count(self, db: Session) -> int:
        """Get total published posts count"""
        return db.query(Post).filter(Post.is_published == True).count()

    async def get_user_posts_count(self, user_id: int, db: Session) -> int:
        """Get user posts count"""
        return db.query(Post).filter(Post.author_id == user_id).count()
