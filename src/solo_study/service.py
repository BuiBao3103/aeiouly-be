import os
import tempfile
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile
import mutagen
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.oggvorbis import OggVorbis

from src.solo_study.models import Sound, BackgroundVideoType, BackgroundVideo, SessionGoal, SessionGoalsStatus
from src.solo_study.schemas import (
    SoundCreate, SoundUpdate, SoundResponse, SoundUploadResponse,
    BackgroundVideoTypeCreate, BackgroundVideoTypeUpdate, BackgroundVideoTypeResponse,
    BackgroundVideoCreate, BackgroundVideoUpdate, BackgroundVideoResponse,
    SessionGoalCreate, SessionGoalUpdate, SessionGoalResponse
)
from src.solo_study.exceptions import (
    SoundNotFoundException, SoundValidationException, SoundUploadException, SoundDeleteException,
    BackgroundVideoTypeNotFoundException, BackgroundVideoTypeValidationException,
    BackgroundVideoNotFoundException, BackgroundVideoValidationException,
    SessionGoalNotFoundException, SessionGoalValidationException
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

    def create_sound(self, sound_data: SoundCreate, db: Session) -> SoundResponse:
        """Create a new sound"""
        try:
            sound = Sound(
                name=sound_data.name,
                sound_file_url=None,  # Will be set when file is uploaded
                file_size=None,       # Will be set when file is uploaded
                duration=None         # Will be set when file is uploaded
            )
            
            db.add(sound)
            db.commit()
            db.refresh(sound)
            
            return SoundResponse.from_orm(sound)
        except Exception as e:
            db.rollback()
            raise SoundValidationException(f"Lỗi khi tạo âm thanh: {str(e)}")

    def get_sounds(self, db: Session, pagination: PaginationParams) -> PaginatedResponse[SoundResponse]:
        """Get all sounds with pagination"""
        try:
            # Get total count
            total = db.query(Sound).filter(Sound.deleted_at.is_(None)).count()
            
            # Get paginated results
            offset = (pagination.page - 1) * pagination.size
            sounds = db.query(Sound).filter(Sound.deleted_at.is_(None)).offset(offset).limit(pagination.size).all()
            
            # Convert to response objects
            sound_responses = [SoundResponse.from_orm(sound) for sound in sounds]
            
            # Return paginated response
            return paginate(sound_responses, total, pagination.page, pagination.size)
        except Exception as e:
            raise SoundValidationException(f"Lỗi khi lấy danh sách âm thanh: {str(e)}")

    def get_sound_by_id(self, sound_id: int, db: Session) -> SoundResponse:
        """Get sound by ID"""
        sound = db.query(Sound).filter(
            Sound.id == sound_id,
            Sound.deleted_at.is_(None)
        ).first()
        
        if not sound:
            raise SoundNotFoundException(f"Không tìm thấy âm thanh với ID {sound_id}")
        
        return SoundResponse.from_orm(sound)

    def update_sound(self, sound_id: int, sound_data: SoundUpdate, db: Session) -> SoundResponse:
        """Update sound"""
        sound = db.query(Sound).filter(
            Sound.id == sound_id,
            Sound.deleted_at.is_(None)
        ).first()
        
        if not sound:
            raise SoundNotFoundException(f"Không tìm thấy âm thanh với ID {sound_id}")
        
        try:
            # Update only name field
            if sound_data.name is not None:
                sound.name = sound_data.name
            
            db.commit()
            db.refresh(sound)
            
            return SoundResponse.from_orm(sound)
        except Exception as e:
            db.rollback()
            raise SoundValidationException(f"Lỗi khi cập nhật âm thanh: {str(e)}")

    def delete_sound(self, sound_id: int, db: Session) -> bool:
        """Soft delete sound"""
        sound = db.query(Sound).filter(
            Sound.id == sound_id,
            Sound.deleted_at.is_(None)
        ).first()
        
        if not sound:
            raise SoundNotFoundException(f"Không tìm thấy âm thanh với ID {sound_id}")
        
        try:
            # Delete file from S3 if exists
            if sound.sound_file_url:
                self.storage_service.delete_file(sound.sound_file_url)
            
            # Soft delete the record
            from datetime import datetime, timezone
            sound.deleted_at = datetime.now(timezone.utc)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise SoundDeleteException(f"Lỗi khi xóa âm thanh: {str(e)}")

    def upload_sound_file(self, sound_id: int, sound_file: UploadFile, db: Session) -> SoundUploadResponse:
        """Upload sound file to AWS S3"""
        # Validate sound file
        if not sound_file.content_type or not sound_file.content_type.startswith("audio/"):
            raise SoundUploadException("File phải là âm thanh (audio/*)")
        
        # Get sound record
        sound = db.query(Sound).filter(
            Sound.id == sound_id,
            Sound.deleted_at.is_(None)
        ).first()
        
        if not sound:
            raise SoundNotFoundException(f"Không tìm thấy âm thanh với ID {sound_id}")
        
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
            sound.file_size = sound_file.size if hasattr(sound_file, 'size') else None
            sound.duration = duration
            
            db.commit()
            db.refresh(sound)
            
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
            db.rollback()
            raise SoundUploadException(f"Lỗi khi upload file âm thanh: {str(e)}")


# BackgroundVideoType Service
class BackgroundVideoTypeService:
    def create_type(self, type_data: BackgroundVideoTypeCreate, db: Session) -> BackgroundVideoTypeResponse:
        """Create a new background video type"""
        try:
            video_type = BackgroundVideoType(
                name=type_data.name,
                description=type_data.description
            )
            
            db.add(video_type)
            db.commit()
            db.refresh(video_type)
            
            return BackgroundVideoTypeResponse.from_orm(video_type)
        except Exception as e:
            db.rollback()
            raise BackgroundVideoTypeValidationException(f"Lỗi khi tạo loại video nền: {str(e)}")

    def get_types(self, db: Session, pagination: PaginationParams) -> PaginatedResponse[BackgroundVideoTypeResponse]:
        """Get all background video types with pagination"""
        try:
            total = db.query(BackgroundVideoType).filter(BackgroundVideoType.deleted_at.is_(None)).count()
            
            offset = (pagination.page - 1) * pagination.size
            types = db.query(BackgroundVideoType).filter(BackgroundVideoType.deleted_at.is_(None)).offset(offset).limit(pagination.size).all()
            
            type_responses = [BackgroundVideoTypeResponse.from_orm(t) for t in types]
            
            return paginate(type_responses, total, pagination.page, pagination.size)
        except Exception as e:
            raise BackgroundVideoTypeValidationException(f"Lỗi khi lấy danh sách loại video nền: {str(e)}")

    def get_type_by_id(self, type_id: int, db: Session) -> BackgroundVideoTypeResponse:
        """Get background video type by ID"""
        video_type = db.query(BackgroundVideoType).filter(
            BackgroundVideoType.id == type_id,
            BackgroundVideoType.deleted_at.is_(None)
        ).first()
        
        if not video_type:
            raise BackgroundVideoTypeNotFoundException(f"Không tìm thấy loại video nền với ID {type_id}")
        
        return BackgroundVideoTypeResponse.from_orm(video_type)

    def update_type(self, type_id: int, type_data: BackgroundVideoTypeUpdate, db: Session) -> BackgroundVideoTypeResponse:
        """Update background video type"""
        video_type = db.query(BackgroundVideoType).filter(
            BackgroundVideoType.id == type_id,
            BackgroundVideoType.deleted_at.is_(None)
        ).first()
        
        if not video_type:
            raise BackgroundVideoTypeNotFoundException(f"Không tìm thấy loại video nền với ID {type_id}")
        
        try:
            if type_data.name is not None:
                video_type.name = type_data.name
            if type_data.description is not None:
                video_type.description = type_data.description
            
            db.commit()
            db.refresh(video_type)
            
            return BackgroundVideoTypeResponse.from_orm(video_type)
        except Exception as e:
            db.rollback()
            raise BackgroundVideoTypeValidationException(f"Lỗi khi cập nhật loại video nền: {str(e)}")

    def delete_type(self, type_id: int, db: Session) -> bool:
        """Soft delete background video type"""
        video_type = db.query(BackgroundVideoType).filter(
            BackgroundVideoType.id == type_id,
            BackgroundVideoType.deleted_at.is_(None)
        ).first()
        
        if not video_type:
            raise BackgroundVideoTypeNotFoundException(f"Không tìm thấy loại video nền với ID {type_id}")
        
        try:
            from datetime import datetime, timezone
            video_type.deleted_at = datetime.now(timezone.utc)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise BackgroundVideoTypeValidationException(f"Lỗi khi xóa loại video nền: {str(e)}")


# BackgroundVideo Service
class BackgroundVideoService:
    def create_video(self, video_data: BackgroundVideoCreate, db: Session) -> BackgroundVideoResponse:
        """Create a new background video"""
        # Check if type exists
        video_type = db.query(BackgroundVideoType).filter(
            BackgroundVideoType.id == video_data.type_id,
            BackgroundVideoType.deleted_at.is_(None)
        ).first()
        
        if not video_type:
            raise BackgroundVideoValidationException(f"Không tìm thấy loại video nền với ID {video_data.type_id}")
        
        try:
            video = BackgroundVideo(
                youtube_url=video_data.youtube_url,
                image_url=None,  # Image will be uploaded separately
                type_id=video_data.type_id
            )
            
            db.add(video)
            db.commit()
            db.refresh(video)
            
            return BackgroundVideoResponse(
                id=video.id,
                youtube_url=video.youtube_url,
                image_url=video.image_url,
                type_id=video.type_id,
                type_name=video_type.name,
                created_at=video.created_at,
                updated_at=video.updated_at
            )
        except Exception as e:
            db.rollback()
            raise BackgroundVideoValidationException(f"Lỗi khi tạo video nền: {str(e)}")

    def get_videos(self, db: Session, pagination: PaginationParams) -> PaginatedResponse[BackgroundVideoResponse]:
        """Get all background videos with pagination"""
        try:
            total = db.query(BackgroundVideo).filter(BackgroundVideo.deleted_at.is_(None)).count()
            
            offset = (pagination.page - 1) * pagination.size
            videos = db.query(BackgroundVideo).filter(BackgroundVideo.deleted_at.is_(None)).offset(offset).limit(pagination.size).all()
            
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
            raise BackgroundVideoValidationException(f"Lỗi khi lấy danh sách video nền: {str(e)}")

    def get_video_by_id(self, video_id: int, db: Session) -> BackgroundVideoResponse:
        """Get background video by ID"""
        video = db.query(BackgroundVideo).filter(
            BackgroundVideo.id == video_id,
            BackgroundVideo.deleted_at.is_(None)
        ).first()
        
        if not video:
            raise BackgroundVideoNotFoundException(f"Không tìm thấy video nền với ID {video_id}")
        
        return BackgroundVideoResponse(
            id=video.id,
            youtube_url=video.youtube_url,
            image_url=video.image_url,
            type_id=video.type_id,
            type_name=video.type.name if video.type else None,
            created_at=video.created_at,
            updated_at=video.updated_at
        )

    def update_video(self, video_id: int, video_data: BackgroundVideoUpdate, db: Session) -> BackgroundVideoResponse:
        """Update background video"""
        video = db.query(BackgroundVideo).filter(
            BackgroundVideo.id == video_id,
            BackgroundVideo.deleted_at.is_(None)
        ).first()
        
        if not video:
            raise BackgroundVideoNotFoundException(f"Không tìm thấy video nền với ID {video_id}")
        
        try:
            # Check if type exists if type_id is being updated
            if video_data.type_id is not None:
                video_type = db.query(BackgroundVideoType).filter(
                    BackgroundVideoType.id == video_data.type_id,
                    BackgroundVideoType.deleted_at.is_(None)
                ).first()
                
                if not video_type:
                    raise BackgroundVideoValidationException(f"Không tìm thấy loại video nền với ID {video_data.type_id}")
                
                video.type_id = video_data.type_id
            
            if video_data.youtube_url is not None:
                video.youtube_url = video_data.youtube_url
            if video_data.image_url is not None:
                video.image_url = video_data.image_url
            
            db.commit()
            db.refresh(video)
            
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
            raise BackgroundVideoValidationException(f"Lỗi khi cập nhật video nền: {str(e)}")

    def delete_video(self, video_id: int, db: Session) -> bool:
        """Soft delete background video"""
        video = db.query(BackgroundVideo).filter(
            BackgroundVideo.id == video_id,
            BackgroundVideo.deleted_at.is_(None)
        ).first()
        
        if not video:
            raise BackgroundVideoNotFoundException(f"Không tìm thấy video nền với ID {video_id}")
        
        try:
            from datetime import datetime, timezone
            video.deleted_at = datetime.now(timezone.utc)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise BackgroundVideoValidationException(f"Lỗi khi xóa video nền: {str(e)}")

    def upload_image(self, video_id: int, image_file: UploadFile, db: Session) -> BackgroundVideoResponse:
        """Upload image file for background video to AWS S3"""
        # Validate image file
        if not image_file.content_type or not image_file.content_type.startswith("image/"):
            raise BackgroundVideoValidationException("File phải là hình ảnh (image/*)")
        
        # Get video record
        video = db.query(BackgroundVideo).filter(
            BackgroundVideo.id == video_id,
            BackgroundVideo.deleted_at.is_(None)
        ).first()
        
        if not video:
            raise BackgroundVideoNotFoundException(f"Không tìm thấy video nền với ID {video_id}")
        
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
            
            db.commit()
            db.refresh(video)
            
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
            raise BackgroundVideoValidationException(f"Lỗi khi upload hình ảnh: {str(e)}")


# SessionGoal Service
class SessionGoalService:
    def create_goal(self, goal_data: SessionGoalCreate, user_id: int, db: Session) -> SessionGoalResponse:
        """Create a new session goal"""
        try:
            goal = SessionGoal(
                goal=goal_data.goal,
                status=goal_data.status or SessionGoalsStatus.OPEN,
                user_id=user_id
            )
            
            db.add(goal)
            db.commit()
            db.refresh(goal)
            
            return SessionGoalResponse.from_orm(goal)
        except Exception as e:
            db.rollback()
            raise SessionGoalValidationException(f"Lỗi khi tạo mục tiêu phiên học: {str(e)}")

    def get_goals(self, user_id: int, db: Session, pagination: PaginationParams, status: Optional[str] = None) -> PaginatedResponse[SessionGoalResponse]:
        """Get all session goals for a user with pagination"""
        try:
            query = db.query(SessionGoal).filter(
                SessionGoal.user_id == user_id,
                SessionGoal.deleted_at.is_(None)
            )
            
            if status:
                query = query.filter(SessionGoal.status == status)
            
            total = query.count()
            
            offset = (pagination.page - 1) * pagination.size
            goals = query.offset(offset).limit(pagination.size).all()
            
            goal_responses = [SessionGoalResponse.from_orm(goal) for goal in goals]
            
            return paginate(goal_responses, total, pagination.page, pagination.size)
        except Exception as e:
            raise SessionGoalValidationException(f"Lỗi khi lấy danh sách mục tiêu phiên học: {str(e)}")

    def get_goal_by_id(self, goal_id: int, user_id: int, db: Session) -> SessionGoalResponse:
        """Get session goal by ID"""
        goal = db.query(SessionGoal).filter(
            SessionGoal.id == goal_id,
            SessionGoal.user_id == user_id,
            SessionGoal.deleted_at.is_(None)
        ).first()
        
        if not goal:
            raise SessionGoalNotFoundException(f"Không tìm thấy mục tiêu phiên học với ID {goal_id}")
        
        return SessionGoalResponse.from_orm(goal)

    def update_goal(self, goal_id: int, goal_data: SessionGoalUpdate, user_id: int, db: Session) -> SessionGoalResponse:
        """Update session goal"""
        goal = db.query(SessionGoal).filter(
            SessionGoal.id == goal_id,
            SessionGoal.user_id == user_id,
            SessionGoal.deleted_at.is_(None)
        ).first()
        
        if not goal:
            raise SessionGoalNotFoundException(f"Không tìm thấy mục tiêu phiên học với ID {goal_id}")
        
        try:
            if goal_data.goal is not None:
                goal.goal = goal_data.goal
            if goal_data.status is not None:
                goal.status = goal_data.status
            
            db.commit()
            db.refresh(goal)
            
            return SessionGoalResponse.from_orm(goal)
        except Exception as e:
            db.rollback()
            raise SessionGoalValidationException(f"Lỗi khi cập nhật mục tiêu phiên học: {str(e)}")

    def delete_goal(self, goal_id: int, user_id: int, db: Session) -> bool:
        """Soft delete session goal"""
        goal = db.query(SessionGoal).filter(
            SessionGoal.id == goal_id,
            SessionGoal.user_id == user_id,
            SessionGoal.deleted_at.is_(None)
        ).first()
        
        if not goal:
            raise SessionGoalNotFoundException(f"Không tìm thấy mục tiêu phiên học với ID {goal_id}")
        
        try:
            from datetime import datetime, timezone
            goal.deleted_at = datetime.now(timezone.utc)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise SessionGoalValidationException(f"Lỗi khi xóa mục tiêu phiên học: {str(e)}")
