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
    @staticmethod
    async def create_post(post_data: PostCreate, current_user: User, db: Session) -> PostResponse:
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

    @staticmethod
    async def upload_post_image(
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
        post = await PostService.get_post_by_id(post_id, db)
        if not post:
            raise PostNotFoundException(f"Không tìm thấy bài viết với ID {post_id}")

        # Check permission
        if post.author_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException("Chỉ tác giả hoặc admin mới có thể upload hình ảnh")

        try:
            # Delete old image if exists
            storage_service = S3StorageService()
            if post.image_url:
                storage_service.delete_file(post.image_url)

            # Upload new image to S3
            url = storage_service.upload_fileobj(image.file, image.content_type, key_prefix="posts/")

            # Update post with new image URL
            post.image_url = url
            db.commit()
            db.refresh(post)

            # Get like info
            likes_count = await PostService.get_post_likes_count(post.id, db)
            is_liked = await PostService.is_post_liked_by_user(post.id, current_user.id, db)

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

    @staticmethod
    async def get_posts(pagination: PaginationParams, db: Session) -> List[Post]:
        """Get all published posts with pagination"""
        query = db.query(Post).filter(Post.is_published == True)

        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        posts = query.order_by(desc(Post.created_at)).offset(
            offset).limit(pagination.size).all()

        return posts

    @staticmethod
    async def get_post_by_id(post_id: int, db: Session) -> Post:
        """Get a specific post by ID"""
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise PostNotFoundException()
        return post

    @staticmethod
    async def get_post_by_id_with_like_info(
        post_id: int,
        current_user: Optional[User],
        db: Session
    ) -> PostResponse:
        """Get a specific post by ID with like information"""
        post = await PostService.get_published_post_by_id(post_id, db)

        likes_count = await PostService.get_post_likes_count(post.id, db)
        is_liked = False
        if current_user:
            is_liked = await PostService.is_post_liked_by_user(post.id, current_user.id, db)

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
    ) -> PostResponse:
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
        
        # Get likes count
        likes_count = db.query(PostLike).filter(PostLike.post_id == post.id).count()
        
        # Check if current user liked this post
        is_liked_by_user = db.query(PostLike).filter(
            PostLike.post_id == post.id,
            PostLike.user_id == current_user.id
        ).first() is not None
        
        # Return PostResponse
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
            is_liked_by_user=is_liked_by_user,
            created_at=post.created_at,
            updated_at=post.updated_at
        )

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
        posts = query.order_by(desc(Post.created_at)).offset(
            offset).limit(pagination.size).all()

        return posts

    @staticmethod
    async def get_posts_by_user_with_like_info(
        user_id: int,
        pagination: PaginationParams,
        current_user: Optional[User],
        db: Session
    ) -> List[PostResponse]:
        """Get all posts by a specific user with like information"""
        posts = await PostService.get_posts_by_user(user_id, pagination, db)

        posts_with_likes = []
        for post in posts:
            likes_count = await PostService.get_post_likes_count(post.id, db)
            is_liked = False
            if current_user:
                is_liked = await PostService.is_post_liked_by_user(post.id, current_user.id, db)

            post_response = PostResponse(
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
            posts_with_likes.append(post_response)

        return posts_with_likes

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

    @staticmethod
    async def like_post(post_id: int, current_user: User, db: Session) -> dict:
        """Like a post"""
        # Kiểm tra post có tồn tại không
        await PostService.get_published_post_by_id(post_id, db)

        # Kiểm tra user đã like post này chưa
        existing_like = db.query(PostLike).filter(
            PostLike.user_id == current_user.id,
            PostLike.post_id == post_id
        ).first()

        if existing_like:
            # Nếu đã like thì unlike
            db.delete(existing_like)
            db.commit()
            is_liked = False
        else:
            # Nếu chưa like thì tạo like mới
            new_like = PostLike(
                user_id=current_user.id,
                post_id=post_id
            )
            db.add(new_like)
            db.commit()
            is_liked = True

        # Đếm tổng số likes
        likes_count = db.query(PostLike).filter(
            PostLike.post_id == post_id).count()

        return {
            "post_id": post_id,
            "is_liked": is_liked,
            "likes_count": likes_count
        }

    @staticmethod
    async def get_post_likes_count(post_id: int, db: Session) -> int:
        """Get total likes count for a post"""
        return db.query(PostLike).filter(PostLike.post_id == post_id).count()

    @staticmethod
    async def is_post_liked_by_user(post_id: int, user_id: int, db: Session) -> bool:
        """Check if a post is liked by a specific user"""
        like = db.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id
        ).first()
        return like is not None

    @staticmethod
    async def get_posts_with_like_info(
        pagination: PaginationParams,
        current_user: Optional[User],
        db: Session
    ) -> List[PostResponse]:
        """Get posts with like information"""
        posts = await PostService.get_posts(pagination, db)

        posts_with_likes = []
        for post in posts:
            likes_count = await PostService.get_post_likes_count(post.id, db)
            is_liked = False
            if current_user:
                is_liked = await PostService.is_post_liked_by_user(post.id, current_user.id, db)

            post_response = PostResponse(
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
            posts_with_likes.append(post_response)

        return posts_with_likes
