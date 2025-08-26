import json
import asyncio
import os
import time
from typing import Dict, Any, List, Optional
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.adk.sessions import DatabaseSessionService
import requests
from src.config import settings

# Initialize DatabaseSessionService at module level
# Use existing app.db instead of creating separate database
db_url = "sqlite:///./app.db"
session_service = DatabaseSessionService(db_url=db_url)

# Output schemas for Gemini API
SCHEMA_GENERATOR = {
    "type": "OBJECT",
    "properties": {
        "paragraph_vi": {"type": "STRING"},
        "sentences_vi": {"type": "ARRAY", "items": {"type": "STRING"}}
    },
    "propertyOrdering": ["paragraph_vi", "sentences_vi"]
}

SCHEMA_FEEDBACK = {
    "type": "OBJECT",
    "properties": {
        "has_error": {"type": "BOOLEAN"},
        "error_type": {"type": "ARRAY", "items": {"type": "STRING"}},
        "feedback": {"type": "STRING"},
        "suggestion": {"type": "STRING"},
        "score": {"type": "NUMBER"}
    },
    "propertyOrdering": ["has_error", "error_type", "feedback", "suggestion", "score"]
}

SCHEMA_SCORING = {
    "type": "OBJECT",
    "properties": {
        "score": {"type": "NUMBER"},
        "summary": {"type": "STRING"},
        "strengths": {"type": "ARRAY", "items": {"type": "STRING"}},
        "areas_to_improve": {"type": "ARRAY", "items": {"type": "STRING"}},
        "next_steps": {"type": "STRING"}
    },
    "propertyOrdering": ["score", "summary", "strengths", "areas_to_improve", "next_steps"]
}

SCHEMA_CHAT_RESPONSE = {
    "type": "OBJECT",
    "properties": {
        "response": {"type": "STRING"},
        "type": {"type": "STRING"},
        "action": {"type": "STRING"}
    },
    "propertyOrdering": ["response", "type", "action"]
}

def call_gemini_api_sync(prompt: str, output_schema: Dict) -> Any:
    """Call Gemini API synchronously"""
    print(f"🔧 DEBUG: Calling Gemini API...")
    
    chat_history = []
    chat_history.append({"role": "user", "parts": [{"text": prompt}]})
    
    payload = {
        "contents": chat_history,
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": output_schema
        }
    }
    
    # Get API key from settings
    api_key = settings.GOOGLE_AI_API_KEY
    if not api_key:
        print("🔧 DEBUG: Warning: GOOGLE_AI_API_KEY not configured!")
        return {}
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
    
    # Retry logic with exponential backoff
    for i in range(3):
        try:
            response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            result = response.json()
            
            if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
                json_text = result["candidates"][0]["content"]["parts"][0]["text"]
                parsed_result = json.loads(json_text)
                return parsed_result
            else:
                print(f"🔧 DEBUG: Error: Unexpected API response structure. Attempt {i+1}.")
                import time
                time.sleep(2 ** i)
        except Exception as e:
            print(f"🔧 DEBUG: API call error: {e}. Attempt {i+1}.")
            import time
            time.sleep(2 ** i)
    
    print(f"🔧 DEBUG: All attempts failed, returning empty dict")
    return {}

def generate_paragraph(topic: str, level: str, length: str, tool_context: ToolContext) -> dict:
    """Generate a Vietnamese paragraph based on topic, level, and length"""
    print(f"🔧 DEBUG: generate_paragraph called with topic: '{topic}', level: '{level}', length: '{length}'")
    
    if not tool_context or not hasattr(tool_context, 'state'):
        print(f"🔧 DEBUG: No tool_context or state found")
        return {
            "status": "error",
            "message": "Không tìm thấy phiên luyện tập."
        }

    prompt = (f"Hãy tạo một đoạn văn mẫu tiếng Việt về chủ đề '{topic}' với độ khó '{level}' và độ dài '{length}' câu. "
              f"Sau đó, hãy tách đoạn văn này thành từng câu riêng biệt và trả về dưới dạng JSON có cấu trúc sau: "
              f"{json.dumps(SCHEMA_GENERATOR)}")
    
    print(f"🔧 DEBUG: Calling Gemini API for paragraph generation...")
    
    # Use synchronous API call to avoid event loop issues
    response = call_gemini_api_sync(prompt, SCHEMA_GENERATOR)
    
    if not response or "paragraph_vi" not in response:
        print(f"🔧 DEBUG: Invalid response from Gemini API")
        return {
            "status": "error",
            "message": "Không thể tạo đoạn văn. Vui lòng thử lại."
        }
    
    # Update session state
    tool_context.state["topic"] = topic
    tool_context.state["level"] = level
    tool_context.state["length"] = length
    tool_context.state["paragraph_vi"] = response.get("paragraph_vi", "")
    tool_context.state["sentences_vi"] = response.get("sentences_vi", [])
    tool_context.state["user_translations_en"] = []
    tool_context.state["feedbacks"] = []
    tool_context.state["current_part_index"] = 0
    tool_context.state["session_start_time"] = int(time.time())
    tool_context.state["statistics"] = {
        "accuracy_rate": 0.0,
        "common_errors": [],
        "strengths": []
    }
    
    print(f"🔧 DEBUG: Generated paragraph with {len(tool_context.state['sentences_vi'])} sentences")
    
    result = {
        "action": "generate_paragraph",
        "paragraph_vi": tool_context.state["paragraph_vi"],
        "sentences_vi": tool_context.state["sentences_vi"],
        "response_type": "instruction"
    }
    
    return result

def submit_translation(translation: str, tool_context: ToolContext) -> dict:
    """Submit user translation and get AI feedback"""
    print(f"🔧 DEBUG: submit_translation called with translation: '{translation}'")
    
    if not tool_context or not hasattr(tool_context, 'state'):
        print(f"🔧 DEBUG: No tool_context or state found")
        return {
            "status": "error",
            "message": "Không tìm thấy phiên luyện tập."
        }
    
    current_index = tool_context.state.get("current_part_index", 0)
    sentences_vi = tool_context.state.get("sentences_vi", [])
    
    if current_index >= len(sentences_vi):
        print(f"🔧 DEBUG: All sentences completed")
        return {
            "status": "error",
            "message": "Bạn đã hoàn thành tất cả các câu dịch."
        }
    
    current_sentence_vi = sentences_vi[current_index]
    
    # Get AI feedback
    prompt = (f"Đây là câu tiếng Việt: '{current_sentence_vi}'\n\n"
              f"Đây là bản dịch tiếng Anh của người dùng: '{translation}'\n\n"
              f"Hãy đánh giá bản dịch này và đưa ra phản hồi chi tiết. Trả về dưới dạng JSON có cấu trúc sau: "
              f"{json.dumps(SCHEMA_FEEDBACK)}")
    
    print(f"🔧 DEBUG: Getting feedback for sentence {current_index + 1}/{len(sentences_vi)}")
    feedback = call_gemini_api_sync(prompt, SCHEMA_FEEDBACK)
    
    # Update session state
    if "user_translations_en" not in tool_context.state:
        tool_context.state["user_translations_en"] = []
    if "feedbacks" not in tool_context.state:
        tool_context.state["feedbacks"] = []
    
    tool_context.state["user_translations_en"].append(translation)
    tool_context.state["feedbacks"].append(feedback)
    tool_context.state["current_part_index"] = current_index + 1
    
    # Update statistics
    update_statistics(tool_context, feedback)
    
    print(f"🔧 DEBUG: Updated state - translations: {len(tool_context.state['user_translations_en'])}, current index: {tool_context.state['current_part_index']}")
    
    # Determine response type based on feedback
    response_type = "feedback"
    if feedback.get("score", 0) >= 8.0:
        response_type = "encouragement"
    
    return {
        "status": "success",
        "feedback": feedback,
        "next_sentence_index": current_index + 1,
        "response_type": response_type
    }

def update_statistics(tool_context: ToolContext, feedback: Dict[str, Any]):
    """Update session statistics based on feedback"""
    stats = tool_context.state.get("statistics", {
        "accuracy_rate": 0.0,
        "common_errors": [],
        "strengths": []
    })
    
    # Calculate accuracy rate
    total_feedbacks = len(tool_context.state.get("feedbacks", []))
    if total_feedbacks > 0:
        total_score = sum(f.get("score", 0) for f in tool_context.state.get("feedbacks", []))
        stats["accuracy_rate"] = total_score / total_feedbacks
    
    # Update common errors
    if feedback.get("has_error") and feedback.get("error_type"):
        for error in feedback["error_type"]:
            if error not in stats["common_errors"]:
                stats["common_errors"].append(error)
    
    # Update strengths
    if feedback.get("score", 0) >= 8.0:  # High score indicates strength
        if "Good vocabulary" in feedback.get("feedback", ""):
            if "Vocabulary" not in stats["strengths"]:
                stats["strengths"].append("Vocabulary")
        if "Good grammar" in feedback.get("feedback", ""):
            if "Grammar" not in stats["strengths"]:
                stats["strengths"].append("Grammar")
    
    tool_context.state["statistics"] = stats

def get_final_summary(tool_context: ToolContext) -> dict:
    """Evaluate overall performance and provide summary"""
    print("--- Tool: get_final_summary called ---")
    
    sentences_vi = tool_context.state.get("sentences_vi", [])
    user_translations_en = tool_context.state.get("user_translations_en", [])
    feedbacks = tool_context.state.get("feedbacks", [])

    if not feedbacks or len(feedbacks) < len(sentences_vi):
        return {
            "action": "get_final_summary",
            "status": "error",
            "message": "Bạn chưa hoàn thành tất cả các câu dịch."
        }
    
    # Get full paragraph and user's complete translation
    full_paragraph_vi = tool_context.state.get("paragraph_vi", "")
    user_full_translation = " ".join(user_translations_en)

    prompt = (f"Đây là đoạn văn gốc tiếng Việt đầy đủ:\n'{full_paragraph_vi}'\n\n"
              f"Đây là bản dịch tiếng Anh hoàn chỉnh của người dùng:\n'{user_full_translation}'\n\n"
              f"Dựa trên bản dịch tổng thể này, hãy đưa ra điểm tổng thể, tóm tắt các điểm mạnh/yếu, "
              f"và đề xuất bài học/chủ đề tiếp theo. Trả về dưới dạng JSON có cấu trúc sau: "
              f"{json.dumps(SCHEMA_SCORING)}")

    # Use synchronous API call to avoid event loop issues
    summary = call_gemini_api_sync(prompt, SCHEMA_SCORING)
    
    # Update session state
    tool_context.state["final_score"] = summary.get("score")
    tool_context.state["final_summary"] = summary.get("summary")
    tool_context.state["next_steps"] = summary.get("next_steps")
    tool_context.state["strengths"] = summary.get("strengths", [])
    tool_context.state["areas_to_improve"] = summary.get("areas_to_improve", [])
    
    return {
        "action": "get_final_summary",
        "summary": summary,
        "response_type": "summary"
    }

def get_session_status(tool_context: ToolContext) -> dict:
    """Get current session status"""
    print("--- Tool: get_session_status called ---")
    state = tool_context.state
    
    status = "in_progress"
    if not state.get("paragraph_vi"):
        status = "not_started"
    elif state.get("current_part_index") >= len(state.get("sentences_vi", [])):
        status = "completed"

    status_info = {
        "status": status,
        "current_step": "generating_paragraph" if not state.get("paragraph_vi") else "translating",
        "current_sentence_index": state.get("current_part_index", 0),
        "total_sentences": len(state.get("sentences_vi", [])),
        "feedback_history": state.get("feedbacks", [])
    }

    return {
        "action": "get_session_status",
        "status": status_info,
        "response_type": "status"
    } 

