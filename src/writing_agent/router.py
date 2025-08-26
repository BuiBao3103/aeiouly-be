import asyncio
from fastapi import APIRouter, Depends, HTTPException, Body, Path, Query
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from .agent import writing_agent, initial_state
from .tools import session_service
from .services import writing_agent_service
from .schemas import (
    CreateSessionRequest, CreateSessionResponse,
    ChatRequest, ChatResponse,
    DashboardResponse, EndSessionResponse
)
import time
from typing import Optional

router = APIRouter(
    prefix="/writing-practice",
    tags=["Writing Practice"],
    responses={404: {"description": "Not found"}},
)

# Phase 1: Setup - Create Session
@router.post("/create-session", response_model=CreateSessionResponse)
async def create_session_endpoint(
    request: CreateSessionRequest,
    user_id: str = Body(..., embed=True)
):
    """Tạo phiên luyện viết mới với đoạn văn mẫu."""
    print(f"🔍 ROUTER: create_session_endpoint called with user_id: {user_id}, topic: {request.topic}")
    
    try:
        # Use service layer to create session
        result = await writing_agent_service.create_session(
            user_id=user_id,
            topic=request.topic,
            level=request.level,
            length=request.length
        )
        
        return CreateSessionResponse(
            session_id=result["session_id"],
            paragraph_vi=result["paragraph_vi"],
            sentences_vi=result["sentences_vi"],
            chat_response=ChatResponse(
                response=result["chat_response"]["response"],
                type=result["chat_response"]["type"]
            )
        )
        
    except Exception as e:
        print(f"🔍 ROUTER: Error in create_session_endpoint: {e}")
        raise e

# Phase 2: Main Interface - Chat
@router.post("/chat/{session_id}", response_model=ChatResponse)
async def chat_endpoint(
    session_id: str = Path(..., description="ID phiên luyện tập"),
    request: ChatRequest = Body(...)
):
    """Xử lý tin nhắn chat với AI tutor."""
    print(f"🔍 ROUTER: Chat endpoint called with session_id: {session_id}")
    print(f"🔍 ROUTER: Request body: {request}")
    
    user_id = request.user_id
    print(f"🔍 ROUTER: User ID: {user_id}")
    
    try:
        # Use service layer to process chat message
        result = await writing_agent_service.process_chat_message(
            user_id=user_id,
            session_id=session_id,
            message=request.request.message
        )
        
        return ChatResponse(
            response=result["response"],
            type=result["type"]
        )
        
    except Exception as e:
        print(f"🔍 ROUTER: Error in chat_endpoint: {e}")
        raise e

# Phase 2: Main Interface - Dashboard
@router.get("/dashboard/{session_id}", response_model=DashboardResponse)
async def dashboard_endpoint(
    session_id: str = Path(..., description="ID phiên luyện tập"),
    user_id: str = Query(..., description="User ID")
):
    """Lấy thông tin dashboard cho phiên luyện tập."""
    # TODO: Implement dashboard logic in service layer
    raise HTTPException(status_code=501, detail="Dashboard endpoint not implemented yet")

# Phase 3: Session End
@router.post("/end-session/{session_id}", response_model=EndSessionResponse)
async def end_session_endpoint(
    session_id: str = Path(..., description="ID phiên luyện tập"),
    user_id: str = Body(..., embed=True)
):
    """Kết thúc phiên luyện tập và nhận đánh giá cuối cùng."""
    # TODO: Implement end session logic in service layer
    raise HTTPException(status_code=501, detail="End session endpoint not implemented yet") 