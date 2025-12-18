from fastapi import HTTPException, status

class PostException(HTTPException):
    """Base exception for post errors"""
    pass

class PostNotFoundException(PostException):
    def __init__(self, detail: str = "Không tìm thấy bài viết"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )

class PostAlreadyExistsException(PostException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bài viết đã tồn tại"
        )

class PostNotPublishedException(PostException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bài viết chưa được xuất bản"
        )

class InsufficientPermissionsException(PostException):
    def __init__(self, custom_message: str = None):
        detail = custom_message if custom_message else "Không đủ quyền để chỉnh sửa bài viết này"
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

class PostValidationException(PostException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        ) 