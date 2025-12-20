import os
import tempfile
import urllib.parse
import urllib.request
import json
import re
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from fastapi import UploadFile
import mutagen
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.oggvorbis import OggVorbis

from src.solo_study.models import Sound, BackgroundVideoType, BackgroundVideo, SessionGoal, SessionGoalsStatus, UserFavoriteVideo
from src.solo_study.schemas import (
    SoundCreate, SoundUpdate, SoundResponse, SoundUploadResponse,
    BackgroundVideoTypeCreate, BackgroundVideoTypeUpdate, BackgroundVideoTypeResponse,
    BackgroundVideoCreate, BackgroundVideoUpdate, BackgroundVideoResponse,
    SessionGoalCreate, SessionGoalUpdate, SessionGoalResponse,
    UserFavoriteVideoCreate, UserFavoriteVideoUpdate, UserFavoriteVideoResponse
)
from src.solo_study.exceptions import (
    SoundNotFoundException, SoundValidationException, SoundUploadException, SoundDeleteException,
    BackgroundVideoTypeNotFoundException, BackgroundVideoTypeValidationException,
    BackgroundVideoNotFoundException, BackgroundVideoValidationException,
    SessionGoalNotFoundException, SessionGoalValidationException,
    UserFavoriteVideoNotFoundException, UserFavoriteVideoValidationException, UserFavoriteVideoAlreadyExistsException
)
from src.storage import S3StorageService
from src.pagination import PaginationParams, PaginatedResponse, paginate


class SoundService:
    def __init__(self):
        self.storage_service = S3StorageService()

    def _get_audio_duration(self, file_path: str) -> Optional[int]:
        """Extract duration from audio file in seconds"""
        try:
            audio_file = mutagen.File(file_path)
            if audio_file is not None:
                duration = int(audio_file.info.length)
                return duration
        except Exception as e:
            print(f"Warning: Could not extract duration from {file_path}: {e}")
        return None

    async def create_sound(self, sound_data: SoundCreate, db: AsyncSession) -> SoundResponse:
        """Create a new sound"""
        try:
            sound = Sound(
                name=sound_data.name,
                sound_file_url=None,  # Will be set when file is uploaded
                file_size=None,       # Will be set when file is uploaded
                duration=None         # Will be set when file is uploaded
            )

            db.add(sound)
            await db.commit()
            await db.refresh(sound)

            return SoundResponse.from_orm(sound)
        except Exception as e:
            await db.rollback()
            raise SoundValidationException(f"Lỗi khi tạo âm thanh: {str(e)}")

    async def get_sounds(self, db: AsyncSession, pagination: PaginationParams) -> PaginatedResponse[SoundResponse]:
        """Get all sounds with pagination"""
        try:
            # Get total count
            count_result = await db.execute(select(func.count(Sound.id)).where(Sound.deleted_at.is_(None)))
            total = count_result.scalar() or 0

            # Get paginated results
            offset = (pagination.page - 1) * pagination.size
            result = await db.execute(
                select(Sound).where(Sound.deleted_at.is_(None)
                                    ).offset(offset).limit(pagination.size)
            )
            sounds = result.scalars().all()

            # Convert to response objects
            sound_responses = [SoundResponse.from_orm(
                sound) for sound in sounds]

            # Return paginated response
            return paginate(sound_responses, total, pagination.page, pagination.size)
        except Exception as e:
            raise SoundValidationException(
                f"Lỗi khi lấy danh sách âm thanh: {str(e)}")

    async def get_sound_by_id(self, sound_id: int, db: AsyncSession) -> SoundResponse:
        """Get sound by ID"""
        result = await db.execute(
            select(Sound).where(
                Sound.id == sound_id,
                Sound.deleted_at.is_(None)
            )
        )
        sound = result.scalar_one_or_none()

        if not sound:
            raise SoundNotFoundException(
                f"Không tìm thấy âm thanh với ID {sound_id}")

        return SoundResponse.from_orm(sound)

    async def update_sound(self, sound_id: int, sound_data: SoundUpdate, db: AsyncSession) -> SoundResponse:
        """Update sound"""
        result = await db.execute(
            select(Sound).where(
                Sound.id == sound_id,
                Sound.deleted_at.is_(None)
            )
        )
        sound = result.scalar_one_or_none()

        if not sound:
            raise SoundNotFoundException(
                f"Không tìm thấy âm thanh với ID {sound_id}")

        try:
            # Update only name field
            if sound_data.name is not None:
                sound.name = sound_data.name

            await db.commit()
            await db.refresh(sound)

            return SoundResponse.from_orm(sound)
        except Exception as e:
            await db.rollback()
            raise SoundValidationException(
                f"Lỗi khi cập nhật âm thanh: {str(e)}")

    async def delete_sound(self, sound_id: int, db: AsyncSession) -> bool:
        """Soft delete sound"""
        result = await db.execute(
            select(Sound).where(
                Sound.id == sound_id,
                Sound.deleted_at.is_(None)
            )
        )
        sound = result.scalar_one_or_none()

        if not sound:
            raise SoundNotFoundException(
                f"Không tìm thấy âm thanh với ID {sound_id}")

        try:
            # Delete file from S3 if exists
            if sound.sound_file_url:
                self.storage_service.delete_file(sound.sound_file_url)

            # Soft delete the record
            from datetime import datetime, timezone
            sound.deleted_at = datetime.now(timezone.utc)

            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise SoundDeleteException(f"Lỗi khi xóa âm thanh: {str(e)}")

    async def upload_sound_file(self, sound_id: int, sound_file: UploadFile, db: AsyncSession) -> SoundUploadResponse:
        """Upload sound file to AWS S3"""
        # Validate sound file
        if not sound_file.content_type or not sound_file.content_type.startswith("audio/"):
            raise SoundUploadException("File phải là âm thanh (audio/*)")

        # Get sound record
        result = await db.execute(
            select(Sound).where(
                Sound.id == sound_id,
                Sound.deleted_at.is_(None)
            )
        )
        sound = result.scalar_one_or_none()

        if not sound:
            raise SoundNotFoundException(
                f"Không tìm thấy âm thanh với ID {sound_id}")

        try:
            # Delete old file if exists
            if sound.sound_file_url:
                self.storage_service.delete_file(sound.sound_file_url)

            # Extract duration BEFORE uploading (file is still available in memory)
            duration = None
            try:
                # Read file to temp location
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                    # Copy file content to temp file
                    sound_file.file.seek(0)  # Reset to beginning
                    content = sound_file.file.read()
                    tmp_file.write(content)
                    tmp_file_path = tmp_file.name

                    # Extract duration
                    duration = self._get_audio_duration(tmp_file_path)

                    # Clean up temp file
                    os.unlink(tmp_file_path)
            except Exception as e:
                print(f"Warning: Could not extract duration: {e}")

            # Reset file pointer to beginning for upload
            sound_file.file.seek(0)

            # Upload new file to S3
            url = self.storage_service.upload_fileobj(
                sound_file.file,
                sound_file.content_type,
                key_prefix="sounds/"
            )

            # Update sound with new file info
            sound.sound_file_url = url
            sound.file_size = sound_file.size if hasattr(
                sound_file, 'size') else None
            sound.duration = duration

            await db.commit()
            await db.refresh(sound)

            return SoundUploadResponse(
                id=sound.id,
                name=sound.name,
                sound_file_url=sound.sound_file_url,
                file_size=sound.file_size,
                duration=sound.duration,
                created_at=sound.created_at,
                updated_at=sound.updated_at
            )
        except Exception as e:
            await db.rollback()
            raise SoundUploadException(
                f"Lỗi khi upload file âm thanh: {str(e)}")


# BackgroundVideoType Service
class BackgroundVideoTypeService:
    async def create_type(self, type_data: BackgroundVideoTypeCreate, db: AsyncSession) -> BackgroundVideoTypeResponse:
        """Create a new background video type"""
        try:
            video_type = BackgroundVideoType(
                name=type_data.name,
                description=type_data.description
            )

            db.add(video_type)
            await db.commit()
            await db.refresh(video_type)

            return BackgroundVideoTypeResponse.from_orm(video_type)
        except Exception as e:
            await db.rollback()
            raise BackgroundVideoTypeValidationException(
                f"Lỗi khi tạo loại video nền: {str(e)}")

    async def get_types(self, db: AsyncSession, pagination: PaginationParams) -> PaginatedResponse[BackgroundVideoTypeResponse]:
        """Get all background video types with pagination"""
        try:
            count_result = await db.execute(
                select(func.count(BackgroundVideoType.id)).where(
                    BackgroundVideoType.deleted_at.is_(None))
            )
            total = count_result.scalar() or 0

            offset = (pagination.page - 1) * pagination.size
            result = await db.execute(
                select(BackgroundVideoType).where(
                    BackgroundVideoType.deleted_at.is_(None))
                .offset(offset).limit(pagination.size)
            )
            types = result.scalars().all()

            type_responses = [
                BackgroundVideoTypeResponse.from_orm(t) for t in types]

            return paginate(type_responses, total, pagination.page, pagination.size)
        except Exception as e:
            raise BackgroundVideoTypeValidationException(
                f"Lỗi khi lấy danh sách loại video nền: {str(e)}")

    async def get_type_by_id(self, type_id: int, db: AsyncSession) -> BackgroundVideoTypeResponse:
        """Get background video type by ID"""
        result = await db.execute(
            select(BackgroundVideoType).where(
                BackgroundVideoType.id == type_id,
                BackgroundVideoType.deleted_at.is_(None)
            )
        )
        video_type = result.scalar_one_or_none()

        if not video_type:
            raise BackgroundVideoTypeNotFoundException(
                f"Không tìm thấy loại video nền với ID {type_id}")

        return BackgroundVideoTypeResponse.from_orm(video_type)

    async def update_type(self, type_id: int, type_data: BackgroundVideoTypeUpdate, db: AsyncSession) -> BackgroundVideoTypeResponse:
        """Update background video type"""
        result = await db.execute(
            select(BackgroundVideoType).where(
                BackgroundVideoType.id == type_id,
                BackgroundVideoType.deleted_at.is_(None)
            )
        )
        video_type = result.scalar_one_or_none()

        if not video_type:
            raise BackgroundVideoTypeNotFoundException(
                f"Không tìm thấy loại video nền với ID {type_id}")

        try:
            if type_data.name is not None:
                video_type.name = type_data.name
            if type_data.description is not None:
                video_type.description = type_data.description

            await db.commit()
            await db.refresh(video_type)

            return BackgroundVideoTypeResponse.from_orm(video_type)
        except Exception as e:
            await db.rollback()
            raise BackgroundVideoTypeValidationException(
                f"Lỗi khi cập nhật loại video nền: {str(e)}")

    async def delete_type(self, type_id: int, db: AsyncSession) -> bool:
        """Soft delete background video type"""
        result = await db.execute(
            select(BackgroundVideoType).where(
                BackgroundVideoType.id == type_id,
                BackgroundVideoType.deleted_at.is_(None)
            )
        )
        video_type = result.scalar_one_or_none()

        if not video_type:
            raise BackgroundVideoTypeNotFoundException(
                f"Không tìm thấy loại video nền với ID {type_id}")

        try:
            from datetime import datetime, timezone
            video_type.deleted_at = datetime.now(timezone.utc)

            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise BackgroundVideoTypeValidationException(
                f"Lỗi khi xóa loại video nền: {str(e)}")


# BackgroundVideo Service
class BackgroundVideoService:
    async def create_video(self, video_data: BackgroundVideoCreate, db: AsyncSession) -> BackgroundVideoResponse:
        """Create a new background video"""
        # Check if type exists
        result = await db.execute(
            select(BackgroundVideoType).where(
                BackgroundVideoType.id == video_data.type_id,
                BackgroundVideoType.deleted_at.is_(None)
            )
        )
        video_type = result.scalar_one_or_none()

        if not video_type:
            raise BackgroundVideoValidationException(
                f"Không tìm thấy loại video nền với ID {video_data.type_id}")

        try:
            video = BackgroundVideo(
                youtube_url=video_data.youtube_url,
                image_url=None,  # Image will be uploaded separately
                type_id=video_data.type_id
            )

            db.add(video)
            await db.commit()
            # Reload video with type relationship
            await db.refresh(video)
            # Eager load type relationship
            result = await db.execute(
                select(BackgroundVideo)
                .options(selectinload(BackgroundVideo.type))
                .where(BackgroundVideo.id == video.id)
            )
            video = result.scalar_one()
            
            return BackgroundVideoResponse(
                id=video.id,
                youtube_url=video.youtube_url,
                image_url=video.image_url,
                type_id=video.type_id,
                type_name=video.type.name if video.type else video_type.name,
                created_at=video.created_at,
                updated_at=video.updated_at
            )
        except Exception as e:
            await db.rollback()
            raise BackgroundVideoValidationException(
                f"Lỗi khi tạo video nền: {str(e)}")

    async def get_videos(self, db: AsyncSession, pagination: PaginationParams, type_id: Optional[int] = None) -> PaginatedResponse[BackgroundVideoResponse]:
        """Get all background videos with pagination, optionally filtered by type_id"""
        try:
            # Build conditions
            conditions = [BackgroundVideo.deleted_at.is_(None)]
            if type_id is not None:
                conditions.append(BackgroundVideo.type_id == type_id)

            # Get total count
            count_result = await db.execute(
                select(func.count(BackgroundVideo.id)).where(and_(*conditions))
            )
            total = count_result.scalar() or 0

            offset = (pagination.page - 1) * pagination.size
            result = await db.execute(
                select(BackgroundVideo)
                .options(selectinload(BackgroundVideo.type))
                .where(and_(*conditions))
                .offset(offset).limit(pagination.size)
            )
            videos = result.scalars().all()

            video_responses = []
            for video in videos:
                video_responses.append(BackgroundVideoResponse(
                    id=video.id,
                    youtube_url=video.youtube_url,
                    image_url=video.image_url,
                    type_id=video.type_id,
                    type_name=video.type.name if video.type else None,
                    created_at=video.created_at,
                    updated_at=video.updated_at
                ))

            return paginate(video_responses, total, pagination.page, pagination.size)
        except Exception as e:
            raise BackgroundVideoValidationException(
                f"Lỗi khi lấy danh sách video nền: {str(e)}")

    async def get_video_by_id(self, video_id: int, db: AsyncSession) -> BackgroundVideoResponse:
        """Get background video by ID"""
        result = await db.execute(
            select(BackgroundVideo)
            .options(selectinload(BackgroundVideo.type))
            .where(
                BackgroundVideo.id == video_id,
                BackgroundVideo.deleted_at.is_(None)
            )
        )
        video = result.scalar_one_or_none()

        if not video:
            raise BackgroundVideoNotFoundException(
                f"Không tìm thấy video nền với ID {video_id}")

        return BackgroundVideoResponse(
            id=video.id,
            youtube_url=video.youtube_url,
            image_url=video.image_url,
            type_id=video.type_id,
            type_name=video.type.name if video.type else None,
            created_at=video.created_at,
            updated_at=video.updated_at
        )

    async def update_video(self, video_id: int, video_data: BackgroundVideoUpdate, db: AsyncSession) -> BackgroundVideoResponse:
        """Update background video"""
        result = await db.execute(
            select(BackgroundVideo)
            .options(selectinload(BackgroundVideo.type))
            .where(
                BackgroundVideo.id == video_id,
                BackgroundVideo.deleted_at.is_(None)
            )
        )
        video = result.scalar_one_or_none()

        if not video:
            raise BackgroundVideoNotFoundException(
                f"Không tìm thấy video nền với ID {video_id}")

        try:
            # Check if type exists if type_id is being updated
            if video_data.type_id is not None:
                type_result = await db.execute(
                    select(BackgroundVideoType).where(
                        BackgroundVideoType.id == video_data.type_id,
                        BackgroundVideoType.deleted_at.is_(None)
                    )
                )
                video_type = type_result.scalar_one_or_none()

                if not video_type:
                    raise BackgroundVideoValidationException(
                        f"Không tìm thấy loại video nền với ID {video_data.type_id}")

                video.type_id = video_data.type_id

            if video_data.youtube_url is not None:
                video.youtube_url = video_data.youtube_url
            if video_data.image_url is not None:
                video.image_url = video_data.image_url

            await db.commit()
            await db.refresh(video, ["type"])  # Refresh with relationship
            
            return BackgroundVideoResponse(
                id=video.id,
                youtube_url=video.youtube_url,
                image_url=video.image_url,
                type_id=video.type_id,
                type_name=video.type.name if video.type else None,
                created_at=video.created_at,
                updated_at=video.updated_at
            )
        except Exception as e:
            await db.rollback()
            raise BackgroundVideoValidationException(
                f"Lỗi khi cập nhật video nền: {str(e)}")

    async def delete_video(self, video_id: int, db: AsyncSession) -> bool:
        """Soft delete background video"""
        result = await db.execute(
            select(BackgroundVideo).where(
                BackgroundVideo.id == video_id,
                BackgroundVideo.deleted_at.is_(None)
            )
        )
        video = result.scalar_one_or_none()

        if not video:
            raise BackgroundVideoNotFoundException(
                f"Không tìm thấy video nền với ID {video_id}")

        try:
            from datetime import datetime, timezone
            video.deleted_at = datetime.now(timezone.utc)

            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise BackgroundVideoValidationException(
                f"Lỗi khi xóa video nền: {str(e)}")

    async def upload_image(self, video_id: int, image_file: UploadFile, db: AsyncSession) -> BackgroundVideoResponse:
        """Upload image file for background video to AWS S3"""
        # Validate image file
        if not image_file.content_type or not image_file.content_type.startswith("image/"):
            raise BackgroundVideoValidationException(
                "File phải là hình ảnh (image/*)")

        # Get video record
        result = await db.execute(
            select(BackgroundVideo)
            .options(selectinload(BackgroundVideo.type))
            .where(
                BackgroundVideo.id == video_id,
                BackgroundVideo.deleted_at.is_(None)
            )
        )
        video = result.scalar_one_or_none()
        
        if not video:
            raise BackgroundVideoNotFoundException(
                f"Không tìm thấy video nền với ID {video_id}")
        
        try:
            # Delete old image if exists
            if video.image_url:
                from src.storage import S3StorageService
                storage_service = S3StorageService()
                storage_service.delete_file(video.image_url)
            
            # Upload new file to S3
            from src.storage import S3StorageService
            storage_service = S3StorageService()
            url = storage_service.upload_fileobj(
                image_file.file, 
                image_file.content_type, 
                key_prefix="background-videos/"
            )
            
            # Update video with new image url
            video.image_url = url
            
            await db.commit()
            await db.refresh(video, ["type"])  # Refresh with relationship
            
            return BackgroundVideoResponse(
                id=video.id,
                youtube_url=video.youtube_url,
                image_url=video.image_url,
                type_id=video.type_id,
                type_name=video.type.name if video.type else None,
                created_at=video.created_at,
                updated_at=video.updated_at
            )
        except Exception as e:
            db.rollback()
            raise BackgroundVideoValidationException(
                f"Lỗi khi upload hình ảnh: {str(e)}")


# SessionGoal Service
class SessionGoalService:
    async def create_goal(self, goal_data: SessionGoalCreate, user_id: int, db: AsyncSession) -> SessionGoalResponse:
        """Create a new session goal"""
        try:
            goal = SessionGoal(
                goal=goal_data.goal,
                status=goal_data.status or SessionGoalsStatus.OPEN,
                user_id=user_id
            )

            db.add(goal)
            await db.commit()
            await db.refresh(goal)

            return SessionGoalResponse.from_orm(goal)
        except Exception as e:
            await db.rollback()
            raise SessionGoalValidationException(
                f"Lỗi khi tạo mục tiêu phiên học: {str(e)}")

    async def get_goals(self, user_id: int, db: AsyncSession, pagination: PaginationParams, status: Optional[str] = None) -> PaginatedResponse[SessionGoalResponse]:
        """Get all session goals for a user with pagination"""
        try:
            # Build conditions
            conditions = [
                SessionGoal.user_id == user_id,
                SessionGoal.deleted_at.is_(None)
            ]
            if status:
                conditions.append(SessionGoal.status == status)

            # Get total count
            count_result = await db.execute(
                select(func.count(SessionGoal.id)).where(and_(*conditions))
            )
            total = count_result.scalar() or 0

            offset = (pagination.page - 1) * pagination.size
            result = await db.execute(
                select(SessionGoal).where(and_(*conditions))
                .offset(offset).limit(pagination.size)
            )
            goals = result.scalars().all()

            goal_responses = [
                SessionGoalResponse.from_orm(goal) for goal in goals]

            return paginate(goal_responses, total, pagination.page, pagination.size)
        except Exception as e:
            raise SessionGoalValidationException(
                f"Lỗi khi lấy danh sách mục tiêu phiên học: {str(e)}")

    async def get_goal_by_id(self, goal_id: int, user_id: int, db: AsyncSession) -> SessionGoalResponse:
        """Get session goal by ID"""
        result = await db.execute(
            select(SessionGoal).where(
                SessionGoal.id == goal_id,
                SessionGoal.user_id == user_id,
                SessionGoal.deleted_at.is_(None)
            )
        )
        goal = result.scalar_one_or_none()

        if not goal:
            raise SessionGoalNotFoundException(
                f"Không tìm thấy mục tiêu phiên học với ID {goal_id}")

        return SessionGoalResponse.from_orm(goal)

    async def update_goal(self, goal_id: int, goal_data: SessionGoalUpdate, user_id: int, db: AsyncSession) -> SessionGoalResponse:
        """Update session goal"""
        result = await db.execute(
            select(SessionGoal).where(
                SessionGoal.id == goal_id,
                SessionGoal.user_id == user_id,
                SessionGoal.deleted_at.is_(None)
            )
        )
        goal = result.scalar_one_or_none()

        if not goal:
            raise SessionGoalNotFoundException(
                f"Không tìm thấy mục tiêu phiên học với ID {goal_id}")

        try:
            if goal_data.goal is not None:
                goal.goal = goal_data.goal
            if goal_data.status is not None:
                goal.status = goal_data.status

            await db.commit()
            await db.refresh(goal)

            return SessionGoalResponse.from_orm(goal)
        except Exception as e:
            await db.rollback()
            raise SessionGoalValidationException(
                f"Lỗi khi cập nhật mục tiêu phiên học: {str(e)}")

    async def delete_goal(self, goal_id: int, user_id: int, db: AsyncSession) -> bool:
        """Soft delete session goal"""
        result = await db.execute(
            select(SessionGoal).where(
                SessionGoal.id == goal_id,
                SessionGoal.user_id == user_id,
                SessionGoal.deleted_at.is_(None)
            )
        )
        goal = result.scalar_one_or_none()

        if not goal:
            raise SessionGoalNotFoundException(
                f"Không tìm thấy mục tiêu phiên học với ID {goal_id}")

        try:
            from datetime import datetime, timezone
            goal.deleted_at = datetime.now(timezone.utc)

            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise SessionGoalValidationException(
                f"Lỗi khi xóa mục tiêu phiên học: {str(e)}")


# UserFavoriteVideo Service
class UserFavoriteVideoService:
    def __init__(self):
        """Initialize UserFavoriteVideoService"""
        pass

    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _get_youtube_metadata(self, video_id: str) -> dict:
        """Get YouTube video metadata using oembed API"""
        oembed_url = "https://www.youtube.com/oembed"
        params = {
            "format": "json",
            "url": f"https://www.youtube.com/watch?v={video_id}"
        }
        query_string = urllib.parse.urlencode(params)
        full_url = f"{oembed_url}?{query_string}"

        try:
            with urllib.request.urlopen(full_url) as response:
                data = json.loads(response.read().decode())
                return {
                    "title": data.get("title", ""),
                    "author_name": data.get("author_name", ""),
                    "author_url": data.get("author_url", ""),
                    "thumbnail_url": data.get("thumbnail_url", ""),
                }
        except Exception as e:
            print("Error fetching YouTube metadata:", e)
            return {
                "title": "",
                "author_name": "",
                "author_url": "",
                "thumbnail_url": ""
            }

    async def create_favorite_video(self, video_data: UserFavoriteVideoCreate, user_id: int, db: AsyncSession) -> UserFavoriteVideoResponse:
        """Create a new favorite video for user"""
        try:
            # Extract video ID from URL
            video_id = self._extract_youtube_video_id(video_data.youtube_url)
            if video_id is None:
                raise UserFavoriteVideoValidationException(
                    "URL YouTube không hợp lệ")

            # Build canonical YouTube URL using only v param
            canonical_url = f"https://www.youtube.com/watch?v={video_id}"

            # Check duplicates by canonical URL
            result = await db.execute(
                select(UserFavoriteVideo).where(
                    UserFavoriteVideo.user_id == user_id,
                    UserFavoriteVideo.youtube_url == canonical_url,
                    UserFavoriteVideo.deleted_at.is_(None)
                )
            )
            existing_video = result.scalar_one_or_none()
            if existing_video:
                raise UserFavoriteVideoAlreadyExistsException(
                    "Video này đã được thêm vào danh sách yêu thích")

            # Get metadata from YouTube
            metadata = self._get_youtube_metadata(video_id)

            # Create new favorite video
            favorite_video = UserFavoriteVideo(
                user_id=user_id,
                youtube_url=canonical_url,
                image_url=metadata.get("thumbnail_url", None),
                name=metadata.get("title", ""),
                author_name=metadata.get("author_name", ""),
                author_url=metadata.get("author_url", "")
            )

            db.add(favorite_video)
            await db.commit()
            await db.refresh(favorite_video)

            return UserFavoriteVideoResponse.from_orm(favorite_video)
        except UserFavoriteVideoAlreadyExistsException:
            raise
        except UserFavoriteVideoValidationException:
            raise
        except Exception as e:
            await db.rollback()
            raise UserFavoriteVideoValidationException(
                f"Lỗi khi tạo video yêu thích: {str(e)}")

    async def get_favorite_videos(self, user_id: int, db: AsyncSession, pagination: PaginationParams) -> PaginatedResponse[UserFavoriteVideoResponse]:
        """Get all favorite videos for a user with pagination"""
        try:
            # Get total count
            count_result = await db.execute(
                select(func.count(UserFavoriteVideo.id)).where(
                    UserFavoriteVideo.user_id == user_id,
                    UserFavoriteVideo.deleted_at.is_(None)
                )
            )
            total = count_result.scalar() or 0

            # Get paginated results
            offset = (pagination.page - 1) * pagination.size
            result = await db.execute(
                select(UserFavoriteVideo).where(
                    UserFavoriteVideo.user_id == user_id,
                    UserFavoriteVideo.deleted_at.is_(None)
                ).offset(offset).limit(pagination.size)
            )
            videos = result.scalars().all()

            # Convert to response objects
            video_responses = [UserFavoriteVideoResponse.from_orm(
                video) for video in videos]

            # Return paginated response
            return paginate(video_responses, total, pagination.page, pagination.size)
        except Exception as e:
            raise UserFavoriteVideoValidationException(
                f"Lỗi khi lấy danh sách video yêu thích: {str(e)}")

    async def get_favorite_video_by_id(self, video_id: int, user_id: int, db: AsyncSession) -> UserFavoriteVideoResponse:
        """Get favorite video by ID"""
        result = await db.execute(
            select(UserFavoriteVideo).where(
                UserFavoriteVideo.id == video_id,
                UserFavoriteVideo.user_id == user_id,
                UserFavoriteVideo.deleted_at.is_(None)
            )
        )
        video = result.scalar_one_or_none()

        if not video:
            raise UserFavoriteVideoNotFoundException(
                f"Không tìm thấy video yêu thích với ID {video_id}")

        return UserFavoriteVideoResponse.from_orm(video)

    async def update_favorite_video(self, video_id: int, video_data: UserFavoriteVideoUpdate, user_id: int, db: AsyncSession) -> UserFavoriteVideoResponse:
        """Update favorite video"""
        result = await db.execute(
            select(UserFavoriteVideo).where(
                UserFavoriteVideo.id == video_id,
                UserFavoriteVideo.user_id == user_id,
                UserFavoriteVideo.deleted_at.is_(None)
            )
        )
        video = result.scalar_one_or_none()

        if not video:
            raise UserFavoriteVideoNotFoundException(
                f"Không tìm thấy video yêu thích với ID {video_id}")

        try:
            if video_data.name is not None:
                video.name = video_data.name

            await db.commit()
            await db.refresh(video)

            return UserFavoriteVideoResponse.from_orm(video)
        except Exception as e:
            await db.rollback()
            raise UserFavoriteVideoValidationException(
                f"Lỗi khi cập nhật video yêu thích: {str(e)}")

    async def delete_favorite_video(self, video_id: int, user_id: int, db: AsyncSession) -> bool:
        """Soft delete favorite video"""
        result = await db.execute(
            select(UserFavoriteVideo).where(
                UserFavoriteVideo.id == video_id,
                UserFavoriteVideo.user_id == user_id,
                UserFavoriteVideo.deleted_at.is_(None)
            )
        )
        video = result.scalar_one_or_none()

        if not video:
            raise UserFavoriteVideoNotFoundException(
                f"Không tìm thấy video yêu thích với ID {video_id}")

        try:
            from datetime import datetime, timezone
            video.deleted_at = datetime.now(timezone.utc)

            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise UserFavoriteVideoValidationException(
                f"Lỗi khi xóa video yêu thích: {str(e)}")
