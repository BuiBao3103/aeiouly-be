"""Router for Chatbot module"""
from fastapi import APIRouter, Depends, HTTPException, status
from src.auth.dependencies import get_current_active_user
from src.users.models import User
from src.chatbot.schemas import ChatbotMessageRequest, ChatbotMessageResponse
from src.chatbot.service import ChatbotService
from src.chatbot.dependencies import get_chatbot_service
from src.chatbot.exceptions import (
    ChatbotAgentException,
    ChatbotMessageSendFailedException,
    ChatbotSessionNotFoundException,
)

router = APIRouter(
    prefix="/chatbot",
    tags=["Chatbot"]
)


@router.post("/message", response_model=ChatbotMessageResponse)
async def send_message(
    message_data: ChatbotMessageRequest,
    current_user: User = Depends(get_current_active_user),
    service: ChatbotService = Depends(get_chatbot_service)
):
    """
    Gửi tin nhắn đến chatbot và nhận phản hồi.
    
    - **message**: Nội dung tin nhắn của người dùng
    - **conversation_id**: (Tùy chọn) ID cuộc trò chuyện. Nếu truyền cùng một ID, backend sẽ tự nhớ lịch sử.
    """
    try:
        response_text, session_id = await service.send_message(
            user_id=str(current_user.id),
            message=message_data.message,
            conversation_id=message_data.conversation_id,
        )
        
        return ChatbotMessageResponse(
            response=response_text,
            conversation_id=session_id,
        )
        
    except ChatbotSessionNotFoundException as e:
        # 404 from service is propagated directly
        raise e
    except ChatbotAgentException as e:
        raise ChatbotMessageSendFailedException(str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi gửi tin nhắn: {str(e)}"
        )

