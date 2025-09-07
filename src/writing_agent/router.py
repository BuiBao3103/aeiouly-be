import asyncio
from fastapi import APIRouter, Depends, HTTPException, Body, Path, Query
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from .agent import writing_agent, initial_state
from google.adk.sessions import DatabaseSessionService
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
    print(f"🔍 ROUTER: Dashboard endpoint called with session_id: {session_id}, user_id: {user_id}")
    
    try:
        # Get runner and session
        runner, current_session_id = await writing_agent_service.get_runner_and_session(user_id, session_id)
        
        # Get session state directly for dashboard
        
        # Get session state for dashboard
        session_service = DatabaseSessionService(db_url="sqlite:///./app.db")
        session = await session_service.get_session(
            app_name="Writing Agent",
            user_id=user_id,
            session_id=session_id
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên luyện tập")
        
        state = session.state
        
        # Build dashboard response
        lesson_info = {
            "topic": state.get("topic", ""),
            "level": state.get("level", ""),
            "length": state.get("length", ""),
            "paragraph_vi": state.get("paragraph_vi", "")
        }
        
        progress = {
            "current_sentence_index": state.get("current_part_index", 0),
            "total_sentences": len(state.get("sentences_vi", [])),
            "completed_sentences": len(state.get("user_translations_en", []))
        }
        
        current_sentence = {
            "text_vi": state.get("sentences_vi", [state.get("current_part_index", 0)])[state.get("current_part_index", 0)] if state.get("sentences_vi") and state.get("current_part_index", 0) < len(state.get("sentences_vi", [])) else "",
            "user_translation": None,
            "feedback": None,
            "status": "pending" if state.get("current_part_index", 0) < len(state.get("sentences_vi", [])) else "completed"
        }
        
        statistics = {
            "accuracy_rate": state.get("statistics", {}).get("accuracy_rate", 0.0),
            "common_errors": state.get("statistics", {}).get("common_errors", []),
            "strengths": state.get("statistics", {}).get("strengths", [])
        }
        
        return DashboardResponse(
            lesson_info=lesson_info,
            progress=progress,
            current_sentence=current_sentence,
            statistics=statistics
        )
        
    except Exception as e:
        print(f"🔍 ROUTER: Error in dashboard_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy thông tin dashboard: {str(e)}")

# Phase 3: Session End
@router.post("/end-session/{session_id}", response_model=EndSessionResponse)
async def end_session_endpoint(
    session_id: str = Path(..., description="ID phiên luyện tập"),
    user_id: str = Body(..., embed=True)
):
    """Kết thúc phiên luyện tập và nhận đánh giá cuối cùng."""
    print(f"🔍 ROUTER: End session endpoint called with session_id: {session_id}, user_id: {user_id}")
    
    try:
        # Get runner and session
        runner, current_session_id = await writing_agent_service.get_runner_and_session(user_id, session_id)
        
        # Get session state directly for final summary
        
        # Get session state for final summary
        session_service = DatabaseSessionService(db_url="sqlite:///./app.db")
        session = await session_service.get_session(
            app_name="Writing Agent",
            user_id=user_id,
            session_id=session_id
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên luyện tập")
        
        state = session.state
        
        # Build end session response
        return EndSessionResponse(
            final_score=state.get("final_score", 0.0),
            detailed_summary=final_response_text or "Không có tóm tắt",
            strengths=state.get("strengths", []),
            areas_to_improve=state.get("areas_to_improve", []),
            next_steps=state.get("next_steps", "Tiếp tục luyện tập"),
            session_duration=state.get("session_duration", 0)
        )
        
    except Exception as e:
        print(f"🔍 ROUTER: Error in end_session_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi kết thúc phiên: {str(e)}") 