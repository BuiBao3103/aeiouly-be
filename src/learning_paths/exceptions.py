from fastapi import HTTPException, status

class LearningPathException(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class LearningPathNotFoundException(LearningPathException):
    def __init__(self, detail: str = "Learning path not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class DailyLessonPlanNotFoundException(LearningPathException):
    def __init__(self, detail: str = "Daily lesson plan not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class UserLessonProgressNotFoundException(LearningPathException):
    def __init__(self, detail: str = "User lesson progress not found"):
        super().__init__(status_code=status.HTTP_404_NOT_NOT_FOUND, detail=detail)

class LearningPathGenerationException(LearningPathException):
    def __init__(self, detail: str = "Failed to generate learning path"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class InvalidLessonStatusException(LearningPathException):
    def __init__(self, detail: str = "Invalid lesson status provided"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class InvalidLessonIndexException(LearningPathException):
    def __init__(self, detail: str = "Lesson index is out of bounds or invalid"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

