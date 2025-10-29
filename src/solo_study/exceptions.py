from fastapi import HTTPException


class SoundException(Exception):
    """Base exception for Sound operations"""
    pass


class SoundNotFoundException(SoundException):
    """Raised when sound is not found"""
    pass


class SoundValidationException(SoundException):
    """Raised when sound validation fails"""
    pass


class SoundUploadException(SoundException):
    """Raised when sound upload fails"""
    pass


class SoundDeleteException(SoundException):
    """Raised when sound deletion fails"""
    pass


# HTTP Exceptions
def sound_not_found_exception(sound_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=f"Không tìm thấy âm thanh với ID {sound_id}"
    )


def sound_validation_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=f"Lỗi validation âm thanh: {message}"
    )


def sound_upload_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=500,
        detail=f"Lỗi upload âm thanh: {message}"
    )


def sound_delete_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=500,
        detail=f"Lỗi xóa âm thanh: {message}"
    )


# BackgroundVideoType Exceptions
class BackgroundVideoTypeException(Exception):
    """Base exception for BackgroundVideoType operations"""
    pass


class BackgroundVideoTypeNotFoundException(BackgroundVideoTypeException):
    """Raised when background video type is not found"""
    pass


class BackgroundVideoTypeValidationException(BackgroundVideoTypeException):
    """Raised when background video type validation fails"""
    pass


def background_video_type_not_found_exception(type_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=f"Không tìm thấy loại video nền với ID {type_id}"
    )


def background_video_type_validation_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=f"Lỗi validation loại video nền: {message}"
    )


# BackgroundVideo Exceptions
class BackgroundVideoException(Exception):
    """Base exception for BackgroundVideo operations"""
    pass


class BackgroundVideoNotFoundException(BackgroundVideoException):
    """Raised when background video is not found"""
    pass


class BackgroundVideoValidationException(BackgroundVideoException):
    """Raised when background video validation fails"""
    pass


def background_video_not_found_exception(video_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=f"Không tìm thấy video nền với ID {video_id}"
    )


def background_video_validation_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=f"Lỗi validation video nền: {message}"
    )


# SessionGoal Exceptions
class SessionGoalException(Exception):
    """Base exception for SessionGoal operations"""
    pass


class SessionGoalNotFoundException(SessionGoalException):
    """Raised when session goal is not found"""
    pass


class SessionGoalValidationException(SessionGoalException):
    """Raised when session goal validation fails"""
    pass


def session_goal_not_found_exception(goal_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=f"Không tìm thấy mục tiêu phiên học với ID {goal_id}"
    )


def session_goal_validation_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=f"Lỗi validation mục tiêu phiên học: {message}"
    )


# UserFavoriteVideo Exceptions
class UserFavoriteVideoException(Exception):
    """Base exception for UserFavoriteVideo operations"""
    pass


class UserFavoriteVideoNotFoundException(UserFavoriteVideoException):
    """Raised when user favorite video is not found"""
    pass


class UserFavoriteVideoValidationException(UserFavoriteVideoException):
    """Raised when user favorite video validation fails"""
    pass


class UserFavoriteVideoAlreadyExistsException(UserFavoriteVideoException):
    """Raised when user favorite video already exists"""
    pass


def user_favorite_video_not_found_exception(video_id: int) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail=f"Không tìm thấy video yêu thích với ID {video_id}"
    )


def user_favorite_video_validation_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=f"Lỗi validation video yêu thích: {message}"
    )


def user_favorite_video_already_exists_exception(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=f"Video yêu thích đã tồn tại: {message}"
    )