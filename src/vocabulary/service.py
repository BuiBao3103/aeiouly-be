from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select, func
import random
import uuid
from datetime import datetime, timezone

from src.vocabulary.models import VocabularySet, VocabularyItem
from src.dictionary.models import Dictionary
from src.vocabulary.schemas import (
    VocabularySetCreate, VocabularySetUpdate, VocabularySetResponse,
    VocabularyItemCreate, VocabularyItemResponse,
    FlashcardSessionResponse, FlashcardResponse,
    MultipleChoiceSessionResponse, MultipleChoiceQuestion, MultipleChoiceOption,
    StudySessionCreate
)
from src.vocabulary.exceptions import (
    VocabularySetNotFoundException, VocabularyItemNotFoundException,
    DictionaryWordNotFoundException, VocabularyItemAlreadyExistsException,
    InsufficientVocabularyException
)
from src.pagination import PaginationParams, PaginatedResponse


class VocabularyService:
    """Service for vocabulary operations"""

    def __init__(self):
        """Initialize VocabularyService"""
        pass
    
    async def ensure_default_vocabulary_set(self, user_id: int, db: AsyncSession) -> VocabularySet:
        """
        Ensure that the user has a default vocabulary set.
        Creates it if missing and returns the VocabularySet instance.
        """
        return await self._get_or_create_default_vocabulary_set(user_id, db)

    async def _get_or_create_default_vocabulary_set(self, user_id: int, db: AsyncSession) -> VocabularySet:
        """Get or create default vocabulary set for user"""
        # Try to find existing default set
        result = await db.execute(
            select(VocabularySet).where(
                and_(
                    VocabularySet.user_id == user_id,
                    VocabularySet.is_default == True,
                    VocabularySet.deleted_at.is_(None)
                )
            )
        )
        default_set = result.scalar_one_or_none()
        
        if default_set:
            return default_set
        
        # Create new default set if not exists
        default_set = VocabularySet(
            user_id=user_id,
            name="Từ vựng của tôi",
            description="Bộ từ vựng mặc định của bạn",
            is_default=True
        )
        
        db.add(default_set)
        await db.commit()
        await db.refresh(default_set)
        
        return default_set

    async def _update_vocabulary_set_count(self, vocabulary_set_id: int, db: AsyncSession):
        """Update total_words count for vocabulary set"""
        count_result = await db.execute(
            select(func.count(VocabularyItem.id)).where(
                and_(
                    VocabularyItem.vocabulary_set_id == vocabulary_set_id,
                    VocabularyItem.deleted_at.is_(None)
                )
            )
        )
        count = count_result.scalar() or 0
        
        result = await db.execute(
            select(VocabularySet).where(VocabularySet.id == vocabulary_set_id)
        )
        vocabulary_set = result.scalar_one_or_none()
        if vocabulary_set:
            vocabulary_set.total_words = count
            await db.commit()

    # Vocabulary Set operations
    async def create_vocabulary_set(self, user_id: int, set_data: VocabularySetCreate, db: AsyncSession) -> VocabularySetResponse:
        """Create a new vocabulary set"""
        vocabulary_set = VocabularySet(
            user_id=user_id,
            name=set_data.name,
            description=set_data.description,
            is_default=False
        )
        
        db.add(vocabulary_set)
        await db.commit()
        await db.refresh(vocabulary_set)
        
        return VocabularySetResponse(
            id=vocabulary_set.id,
            user_id=vocabulary_set.user_id,
            name=vocabulary_set.name,
            description=vocabulary_set.description,
            is_default=vocabulary_set.is_default,
            total_words=vocabulary_set.total_words,
            created_at=vocabulary_set.created_at,
            updated_at=vocabulary_set.updated_at
        )

    async def get_vocabulary_sets(self, user_id: int, db: AsyncSession, pagination: PaginationParams) -> PaginatedResponse[VocabularySetResponse]:
        """Get user's vocabulary sets"""
        # Get total count
        count_result = await db.execute(
            select(func.count(VocabularySet.id)).where(
                and_(
                    VocabularySet.user_id == user_id,
                    VocabularySet.deleted_at.is_(None)
                )
            )
        )
        total = count_result.scalar() or 0
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        result = await db.execute(
            select(VocabularySet).where(
                and_(
                    VocabularySet.user_id == user_id,
                    VocabularySet.deleted_at.is_(None)
                )
            ).order_by(VocabularySet.created_at.desc()).offset(offset).limit(pagination.size)
        )
        vocabulary_sets = result.scalars().all()
        
        result = []
        for vs in vocabulary_sets:
            result.append(VocabularySetResponse(
                id=vs.id,
                user_id=vs.user_id,
                name=vs.name,
                description=vs.description,
                is_default=vs.is_default,
                total_words=vs.total_words,
                created_at=vs.created_at,
                updated_at=vs.updated_at
            ))
        
        # Create paginated response
        from src.pagination import paginate
        return paginate(result, total, pagination.page, pagination.size)

    async def get_vocabulary_set_by_id(self, user_id: int, set_id: int, db: AsyncSession) -> VocabularySetResponse:
        """Get vocabulary set by ID"""
        result = await db.execute(
            select(VocabularySet).where(
                and_(
                    VocabularySet.id == set_id,
                    VocabularySet.user_id == user_id,
                    VocabularySet.deleted_at.is_(None)
                )
            )
        )
        vocabulary_set = result.scalar_one_or_none()
        
        if not vocabulary_set:
            raise VocabularySetNotFoundException(f"Không tìm thấy bộ từ vựng {set_id}")
        
        return VocabularySetResponse(
            id=vocabulary_set.id,
            user_id=vocabulary_set.user_id,
            name=vocabulary_set.name,
            description=vocabulary_set.description,
            is_default=vocabulary_set.is_default,
            total_words=vocabulary_set.total_words,
            created_at=vocabulary_set.created_at,
            updated_at=vocabulary_set.updated_at
        )

    async def update_vocabulary_set(self, user_id: int, set_id: int, set_data: VocabularySetUpdate, db: AsyncSession) -> VocabularySetResponse:
        """Update vocabulary set"""
        result = await db.execute(
            select(VocabularySet).where(
                and_(
                    VocabularySet.id == set_id,
                    VocabularySet.user_id == user_id,
                    VocabularySet.deleted_at.is_(None)
                )
            )
        )
        vocabulary_set = result.scalar_one_or_none()
        
        if not vocabulary_set:
            raise VocabularySetNotFoundException(f"Không tìm thấy bộ từ vựng {set_id}")
        
        if set_data.name is not None:
            vocabulary_set.name = set_data.name
        if set_data.description is not None:
            vocabulary_set.description = set_data.description
        
        await db.commit()
        await db.refresh(vocabulary_set)
        
        return VocabularySetResponse(
            id=vocabulary_set.id,
            user_id=vocabulary_set.user_id,
            name=vocabulary_set.name,
            description=vocabulary_set.description,
            is_default=vocabulary_set.is_default,
            total_words=vocabulary_set.total_words,
            created_at=vocabulary_set.created_at,
            updated_at=vocabulary_set.updated_at
        )

    async def delete_vocabulary_set(self, user_id: int, set_id: int, db: AsyncSession) -> bool:
        """Soft delete vocabulary set"""
        result = await db.execute(
            select(VocabularySet).where(
                and_(
                    VocabularySet.id == set_id,
                    VocabularySet.user_id == user_id,
                    VocabularySet.deleted_at.is_(None)
                )
            )
        )
        vocabulary_set = result.scalar_one_or_none()
        
        if not vocabulary_set:
            raise VocabularySetNotFoundException(f"Không tìm thấy bộ từ vựng {set_id}")
        
        # Soft delete by setting deleted_at
        vocabulary_set.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        return True

    # Vocabulary Item operations
    async def add_vocabulary_item(self, user_id: int, item_data: VocabularyItemCreate, db: AsyncSession) -> VocabularyItemResponse:
        """Add vocabulary item to set"""
        # Determine which vocabulary set to use
        if item_data.use_default_set:
            # Get or create default vocabulary set
            vocabulary_set = await self._get_or_create_default_vocabulary_set(user_id, db)
            vocabulary_set_id = vocabulary_set.id
        else:
            # Use specified vocabulary set
            if not item_data.vocabulary_set_id:
                raise ValueError("vocabulary_set_id is required when use_default_set is False")
            
            result = await db.execute(
                select(VocabularySet).where(
                    and_(
                        VocabularySet.id == item_data.vocabulary_set_id,
                        VocabularySet.user_id == user_id,
                        VocabularySet.deleted_at.is_(None)
                    )
                )
            )
            vocabulary_set = result.scalar_one_or_none()
            
            if not vocabulary_set:
                raise VocabularySetNotFoundException(f"Không tìm thấy bộ từ vựng {item_data.vocabulary_set_id}")
            
            vocabulary_set_id = item_data.vocabulary_set_id
        
        # Check if dictionary word exists
        result = await db.execute(
            select(Dictionary).where(
                and_(
                    Dictionary.id == item_data.dictionary_id,
                    Dictionary.deleted_at.is_(None)
                )
            )
        )
        dictionary_word = result.scalar_one_or_none()
        
        if not dictionary_word:
            raise DictionaryWordNotFoundException(f"Không tìm thấy từ trong từ điển {item_data.dictionary_id}")
        
        # Check if item already exists
        result = await db.execute(
            select(VocabularyItem).where(
                and_(
                    VocabularyItem.user_id == user_id,
                    VocabularyItem.vocabulary_set_id == vocabulary_set_id,
                    VocabularyItem.dictionary_id == item_data.dictionary_id,
                    VocabularyItem.deleted_at.is_(None)
                )
            )
        )
        existing_item = result.scalar_one_or_none()
        
        if existing_item:
            raise VocabularyItemAlreadyExistsException("Từ vựng đã tồn tại trong bộ từ vựng")
        
        vocabulary_item = VocabularyItem(
            user_id=user_id,
            vocabulary_set_id=vocabulary_set_id,
            dictionary_id=item_data.dictionary_id
        )
        
        db.add(vocabulary_item)
        await db.commit()
        await db.refresh(vocabulary_item)
        
        # Update vocabulary set count
        await self._update_vocabulary_set_count(vocabulary_set_id, db)
        
        return VocabularyItemResponse(
            id=vocabulary_item.id,
            user_id=vocabulary_item.user_id,
            vocabulary_set_id=vocabulary_item.vocabulary_set_id,
            dictionary_id=vocabulary_item.dictionary_id,
            created_at=vocabulary_item.created_at,
            updated_at=vocabulary_item.updated_at,
            word=dictionary_word.expression,
            definitions=dictionary_word.definitions
        )

    async def get_vocabulary_items(self, user_id: int, set_id: int, db: AsyncSession, pagination: PaginationParams) -> PaginatedResponse[VocabularyItemResponse]:
        """Get vocabulary items in a set"""
        # Get total count
        count_result = await db.execute(
            select(func.count(VocabularyItem.id)).select_from(
                VocabularyItem.join(Dictionary, VocabularyItem.dictionary_id == Dictionary.id)
            ).where(
                and_(
                    VocabularyItem.user_id == user_id,
                    VocabularyItem.vocabulary_set_id == set_id,
                    VocabularyItem.deleted_at.is_(None),
                    Dictionary.deleted_at.is_(None)
                )
            )
        )
        total = count_result.scalar() or 0
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        result = await db.execute(
            select(VocabularyItem, Dictionary).join(
                Dictionary, VocabularyItem.dictionary_id == Dictionary.id
            ).where(
                and_(
                    VocabularyItem.user_id == user_id,
                    VocabularyItem.vocabulary_set_id == set_id,
                    VocabularyItem.deleted_at.is_(None),
                    Dictionary.deleted_at.is_(None)
                )
            ).order_by(VocabularyItem.created_at.desc()).offset(offset).limit(pagination.size)
        )
        items = result.all()
        
        result = []
        for item, dictionary in items:
            result.append(VocabularyItemResponse(
                id=item.id,
                user_id=item.user_id,
                vocabulary_set_id=item.vocabulary_set_id,
                dictionary_id=item.dictionary_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                word=dictionary.expression,
                definitions=dictionary.definitions
            ))
        
        # Create paginated response
        from src.pagination import paginate
        return paginate(result, total, pagination.page, pagination.size)

    async def remove_vocabulary_item(self, user_id: int, item_id: int, db: AsyncSession) -> bool:
        """Remove vocabulary item from set"""
        result = await db.execute(
            select(VocabularyItem).where(
                and_(
                    VocabularyItem.id == item_id,
                    VocabularyItem.user_id == user_id,
                    VocabularyItem.deleted_at.is_(None)
                )
            )
        )
        vocabulary_item = result.scalar_one_or_none()
        
        if not vocabulary_item:
            raise VocabularyItemNotFoundException(f"Không tìm thấy từ vựng {item_id}")
        
        # Soft delete by setting deleted_at
        vocabulary_item.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        
        # Update vocabulary set count
        await self._update_vocabulary_set_count(vocabulary_item.vocabulary_set_id, db)
        
        return True

    # Study operations
    async def create_flashcard_session(self, user_id: int, session_data: StudySessionCreate, db: AsyncSession) -> FlashcardSessionResponse:
        """Create flashcard study session"""
        # Get vocabulary items
        result = await db.execute(
            select(VocabularyItem, Dictionary).join(
                Dictionary, VocabularyItem.dictionary_id == Dictionary.id
            ).where(
                and_(
                    VocabularyItem.user_id == user_id,
                    VocabularyItem.vocabulary_set_id == session_data.vocabulary_set_id,
                    VocabularyItem.deleted_at.is_(None),
                    Dictionary.deleted_at.is_(None)
                )
            ).limit(session_data.max_items)
        )
        items = result.all()
        
        if len(items) < 1:
            raise InsufficientVocabularyException("Không đủ từ vựng để tạo phiên học")
        
        # Shuffle items
        random.shuffle(items)
        
        # Create flashcards
        flashcards = []
        for item, dictionary in items:
            flashcards.append(FlashcardResponse(
                id=item.id,
                word=dictionary.expression,
                definitions=dictionary.definitions
            ))
        
        session_id = str(uuid.uuid4())
        
        return FlashcardSessionResponse(
            session_id=session_id,
            vocabulary_set_id=session_data.vocabulary_set_id,
            total_cards=len(flashcards),
            current_card=0,
            cards=flashcards
        )

    async def create_multiple_choice_session(self, user_id: int, session_data: StudySessionCreate, db: AsyncSession) -> MultipleChoiceSessionResponse:
        """Create multiple choice study session"""
        # Get vocabulary items
        result = await db.execute(
            select(VocabularyItem, Dictionary).join(
                Dictionary, VocabularyItem.dictionary_id == Dictionary.id
            ).where(
                and_(
                    VocabularyItem.user_id == user_id,
                    VocabularyItem.vocabulary_set_id == session_data.vocabulary_set_id,
                    VocabularyItem.deleted_at.is_(None),
                    Dictionary.deleted_at.is_(None)
                )
            ).limit(session_data.max_items)
        )
        items = result.all()
        
        if len(items) < 4:
            raise InsufficientVocabularyException("Cần ít nhất 4 từ vựng để tạo phiên học trắc nghiệm")
        
        # Shuffle items
        random.shuffle(items)
        
        # Create questions
        questions = []
        for item, dictionary in items:
            # Get 3 random wrong answers
            other_items = [d for d in items if d[1].id != dictionary.id]
            wrong_options = random.sample(other_items, min(3, len(other_items)))
            
            options = []
            
            # Add correct answer
            options.append(MultipleChoiceOption(
                option_id="A",
                text=dictionary.definitions,
                is_correct=True
            ))
            
            # Add wrong answers
            option_ids = ["B", "C", "D"]
            for i, (_, wrong_dict) in enumerate(wrong_options):
                options.append(MultipleChoiceOption(
                    option_id=option_ids[i],
                    text=wrong_dict.definitions,
                    is_correct=False
                ))
            
            # Shuffle options
            random.shuffle(options)
            
            questions.append(MultipleChoiceQuestion(
                id=item.id,
                word=dictionary.expression,
                options=options
            ))
        
        session_id = str(uuid.uuid4())
        
        return MultipleChoiceSessionResponse(
            session_id=session_id,
            vocabulary_set_id=session_data.vocabulary_set_id,
            total_questions=len(questions),
            current_question=0,
            questions=questions
        )
