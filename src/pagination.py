from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field
from fastapi import Query

T = TypeVar('T')

class PaginationParams(BaseModel):
    page: int = Field(Query(1, ge=1, description="Page number"))
    size: int = Field(Query(10, ge=1, le=100, description="Page size"))

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def next_page(self) -> int:
        return self.page + 1 if self.has_next else None

    @property
    def prev_page(self) -> int:
        return self.page - 1 if self.has_prev else None

def paginate(items: List[T], total: int, page: int, size: int) -> PaginatedResponse[T]:
    """
    Create a paginated response
    """
    pages = (total + size - 1) // size  # Ceiling division
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )

def get_offset(page: int, size: int) -> int:
    """
    Calculate offset for pagination
    """
    return (page - 1) * size 