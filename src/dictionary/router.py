from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional
from src.database import get_db
from src.dictionary.service import DictionaryService
from src.dictionary.schemas import (
    DictionarySearchRequest, 
    DictionarySearchResponse, 
    DictionaryResponse,
    TranslationRequest,
    TranslationResponse
)
from src.dictionary.dependencies import get_dictionary_service

router = APIRouter(prefix="/dictionary", tags=["Dictionary"])


@router.get("/search", response_model=DictionarySearchResponse)
async def search_words(
    query: str = Query(..., min_length=1, max_length=100, description="Từ khóa tìm kiếm"),
    limit: Optional[int] = Query(10, ge=1, le=50, description="Số lượng kết quả tối đa"),
    service: DictionaryService = Depends(get_dictionary_service),
    db: Session = Depends(get_db)
):
    """
    Tìm kiếm từ vựng trong từ điển Anh-Việt (chỉ tìm trong expression)
    
    - **query**: Từ khóa tìm kiếm (1-100 ký tự)
    - **limit**: Số lượng kết quả tối đa (1-50, mặc định 10)
    """
    request = DictionarySearchRequest(query=query, limit=limit)
    try:
        return await service.search_words(db, request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi tìm kiếm từ vựng: {str(e)}"
        )


@router.get("/word/{word_id}", response_model=DictionaryResponse)
async def get_word_by_id(
    word_id: int = Path(..., description="ID của từ vựng"),
    service: DictionaryService = Depends(get_dictionary_service),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin từ vựng theo ID
    """
    result = await service.get_word_by_id(db, word_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy từ vựng với ID này"
        )
    return result


@router.get("/word", response_model=DictionaryResponse)
async def get_word_by_expression(
    expression: str = Query(..., description="Từ vựng cần tìm"),
    service: DictionaryService = Depends(get_dictionary_service),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin từ vựng theo từ chính xác
    """
    result = await service.get_word_by_expression(db, expression)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy từ '{expression}' trong từ điển"
        )
    return result


@router.get("/find", response_model=DictionaryResponse)
async def find_single_word_with_suffixes(
    word: str = Query(..., min_length=1, max_length=50, description="Từ vựng cần tìm (hỗ trợ suffixes)"),
    service: DictionaryService = Depends(get_dictionary_service),
    db: Session = Depends(get_db)
):
    """
    Tìm 1 từ duy nhất với hỗ trợ suffixes (stemming)
    
    Ví dụ:
    - "printed" -> tìm "print"
    - "running" -> tìm "run" 
    - "happier" -> tìm "happy"
    - "beautifully" -> tìm "beautiful"
    
    - **word**: Từ vựng cần tìm (1-50 ký tự)
    """
    result = await service.find_single_word_with_suffixes(db, word)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy từ '{word}' hoặc từ gốc của nó trong từ điển"
        )
    return result


@router.get("/random", response_model=list[DictionaryResponse])
async def get_random_words(
    limit: int = Query(10, ge=1, le=50, description="Số lượng từ ngẫu nhiên"),
    service: DictionaryService = Depends(get_dictionary_service),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách từ vựng ngẫu nhiên
    """
    try:
        return await service.get_random_words(db, limit)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy từ ngẫu nhiên: {str(e)}"
        )


@router.get("/stats")
async def get_dictionary_stats(db: Session = Depends(get_db)):
    """
    Lấy thống kê chi tiết từ điển
    """
    try:
        from sqlalchemy import func, text
        from src.dictionary.models import Dictionary
        
        # Basic stats
        total_words = db.query(func.count(Dictionary.id)).scalar()
        
        # Average definition length
        avg_def_length = db.query(func.avg(func.length(Dictionary.definitions))).scalar()
        
        # Longest definition
        longest_def = db.query(
            Dictionary.expression, 
            func.length(Dictionary.definitions).label('def_length')
        ).order_by(func.length(Dictionary.definitions).desc()).first()
        
        # Shortest definition
        shortest_def = db.query(
            Dictionary.expression, 
            func.length(Dictionary.definitions).label('def_length')
        ).order_by(func.length(Dictionary.definitions).asc()).first()
        
        # Words starting with each letter
        letter_stats = db.query(
            func.upper(func.left(Dictionary.expression, 1)).label('letter'),
            func.count(Dictionary.id).label('count')
        ).group_by(func.upper(func.left(Dictionary.expression, 1))).order_by('letter').all()
        
        # Most common word lengths
        word_length_stats = db.query(
            func.length(Dictionary.expression).label('word_length'),
            func.count(Dictionary.id).label('count')
        ).group_by(func.length(Dictionary.expression)).order_by('word_length').limit(10).all()
        
        return {
            "overview": {
                "total_words": total_words,
                "message": f"Từ điển hiện có {total_words:,} từ vựng"
            },
            "definition_stats": {
                "average_length": round(avg_def_length, 2) if avg_def_length else 0,
                "longest_definition": {
                    "word": longest_def.expression if longest_def else None,
                    "length": longest_def.def_length if longest_def else 0
                },
                "shortest_definition": {
                    "word": shortest_def.expression if shortest_def else None,
                    "length": shortest_def.def_length if shortest_def else 0
                }
            },
            "letter_distribution": [
                {"letter": stat.letter, "count": stat.count} 
                for stat in letter_stats
            ],
            "word_length_distribution": [
                {"length": stat.word_length, "count": stat.count} 
                for stat in word_length_stats
            ],
            "database_info": {
                "table_name": "dictionary",
                "indexes": ["ix_dictionary_expression"],
                "search_method": "ILIKE pattern matching"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy thống kê: {str(e)}"
        )


@router.post("/translate", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest,
    service: DictionaryService = Depends(get_dictionary_service)
):
    """
    Dịch văn bản sang ngôn ngữ khác
    
    - **text**: Văn bản cần dịch (1-5000 ký tự)
    - **source_language**: Mã ngôn ngữ nguồn (mặc định: vi)
    - **target_language**: Mã ngôn ngữ đích (mặc định: en)
    """
    try:
        return await service.translate_text(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi dịch văn bản: {str(e)}"
        )
