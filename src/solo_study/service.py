import os
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile
import mutagen
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.oggvorbis import OggVorbis

from src.solo_study.models import Sound
from src.solo_study.schemas import SoundCreate, SoundUpdate, SoundResponse, SoundUploadResponse
from src.solo_study.exceptions import (
    SoundNotFoundException,
    SoundValidationException,
    SoundUploadException,
    SoundDeleteException
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
            
            # Upload new file to S3
            url = self.storage_service.upload_fileobj(
                sound_file.file, 
                sound_file.content_type, 
                key_prefix="sounds/"
            )
            
            # Update sound with new file info
            sound.sound_file_url = url
            sound.file_size = sound_file.size if hasattr(sound_file, 'size') else None
            
            # Extract duration from audio file
            duration = None
            if hasattr(sound_file, 'file') and hasattr(sound_file.file, 'name'):
                # If file has a temporary path, extract duration
                duration = self._get_audio_duration(sound_file.file.name)
            elif hasattr(sound_file, 'filename') and sound_file.filename:
                # Try to extract from filename if it's a local file
                try:
                    duration = self._get_audio_duration(sound_file.filename)
                except Exception:
                    pass
            
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
