from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field
from fastapi import Query

T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    message: str = Field(..., description="Mô tả kết quả của yêu cầu")
    code: str = Field(..., description="Mã định danh kết quả của yêu cầu")
    data: T = Field(..., description="Dữ liệu trả về của yêu cầu")
    success: bool = Field(..., description="Trạng thái thành công của yêu cầu")


def create_response(data: T, message: str = "Thành công", code: str = "SUCCESS") -> BaseResponse[T]:
    """
    Tạo một phản hồi cơ bản
    """
    return BaseResponse(
        message=message,
        code=code,
        data=data,
        success=True
    )


def create_error_response(message: str, code: str) -> BaseResponse[None]:
    """
    Tạo một phản hồi lỗi cơ bản
    """
    return BaseResponse(
        message=message,
        code=code,
        data=None,
        success=False
    )


def create_empty_response(message: str = "Không có dữ liệu", code: str = "NO_DATA") -> BaseResponse[None]:
    """
    Tạo một phản hồi trống cơ bản
    """
    return BaseResponse(
        message=message,
        code=code,
        data=None,
        success=True
    )


def create_custom_response(data: T, message: str, code: str, success: bool) -> BaseResponse[T]:
    """
    Tạo một phản hồi tùy chỉnh cơ bản
    """
    return BaseResponse(
        message=message,
        code=code,
        data=data,
        success=success
    )
