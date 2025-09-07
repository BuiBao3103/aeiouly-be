import asyncio
from typing import Optional, Dict, Any
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from fastapi import HTTPException
from .agent import writing_agent, initial_state
from google.adk.sessions import DatabaseSessionService
from src.config import settings
import time

# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

class WritingAgentService:
    """Service class for writing agent operations"""
    
    def __init__(self):
        # Initialize DatabaseSessionService
        db_url = "sqlite:///./app.db"
        self.session_service = DatabaseSessionService(db_url=db_url)
    
    async def get_runner_and_session(self, user_id: str, session_id: Optional[str] = None):
        """Get or create runner and session for user"""
        print(f"🔧 SERVICE: Getting runner and session for user: {user_id}")
        
        try:
            # Get existing session if session_id provided
            if session_id:
                session = await self.session_service.get_session(
                    app_name="Writing Agent",
                    user_id=user_id,
                    session_id=session_id
                )
            else:
                session = await self.session_service.create_session(
                    app_name="Writing Agent",
                    user_id=user_id
                )
            
            if not session:
                raise HTTPException(status_code=404, detail="Không thể tạo hoặc tìm thấy phiên luyện tập")
            
            # Create runner
            runner = Runner(
                agent=writing_agent,
                app_name="Writing Agent",
                session_service=self.session_service,
            )
            
            return runner, session_id or session.id
            
        except Exception as e:
            print(f"🔧 SERVICE: Error in get_runner_and_session: {e}")
            raise HTTPException(status_code=500, detail=f"Lỗi khi tạo runner và session: {str(e)}")
    
    async def process_agent_response(self, event):
        """Process and display agent response events."""
        # Check for final response
        final_response = None
        if event.is_final_response():
            if (
                event.content
                and event.content.parts
                and hasattr(event.content.parts[0], "text")
                and event.content.parts[0].text
            ):
                final_response = event.content.parts[0].text.strip()
                # Use colors and formatting to make the final response stand out
                print(
                    f"\n{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╔══ AGENT RESPONSE ═════════════════════════════════════════{Colors.RESET}"
                )
                print(f"{Colors.CYAN}{Colors.BOLD}{final_response}{Colors.RESET}")
                print(
                    f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╚═════════════════════════════════════════════════════════════{Colors.RESET}\n"
                )

        return final_response
    
    def extract_tool_feedback(self, response_text: str) -> tuple:
        """Extract actual feedback text and response type from tool output responses."""
        print(f"🔧 SERVICE: Extracting tool feedback from: {response_text}")
        
        response_type = "feedback"  # Default type
        
        # Check if it's a tool output response (contains ```tool_outputs)
        if "```tool_outputs" in response_text:
            print(f"🔧 SERVICE: Detected tool output response, extracting feedback...")
            # Extract the tool output content
            start_marker = "```tool_outputs\n"
            end_marker = "\n```"
            
            if start_marker in response_text and end_marker in response_text:
                tool_output_content = response_text.split(start_marker)[1].split(end_marker)[0]
                print(f"🔧 SERVICE: Tool output content: {tool_output_content}")
                
                # Try to extract feedback from the tool output
                try:
                    import ast
                    # Parse the tool output as a Python dict
                    tool_output_dict = ast.literal_eval(tool_output_content)
                    print(f"🔧 SERVICE: Parsed tool output: {tool_output_dict}")
                    
                    # Extract feedback from the nested structure
                    if 'submit_translation_response' in tool_output_dict:
                        translation_response = tool_output_dict['submit_translation_response']
                        if 'feedback' in translation_response:
                            feedback = translation_response['feedback']
                            if 'overall_feedback' in feedback:
                                response_text = feedback['overall_feedback']
                                print(f"🔧 SERVICE: Extracted overall_feedback: {response_text}")
                            else:
                                response_text = str(feedback)
                        else:
                            response_text = str(translation_response)
                        
                        # Extract response type from tool result
                        if 'response_type' in tool_output_dict:
                            response_type = tool_output_dict['response_type']
                    else:
                        response_text = str(tool_output_dict)
                        # Extract response type from tool result
                        if 'response_type' in tool_output_dict:
                            response_type = tool_output_dict['response_type']
                        
                except Exception as parse_error:
                    print(f"🔧 SERVICE: Error parsing tool output: {parse_error}")
                    # Fallback: extract text between the markers
                    response_text = tool_output_content
            else:
                response_text = response_text
        else:
            # Regular text response, just return as is
            response_text = response_text
        
        print(f"🔧 SERVICE: Final extracted feedback: {response_text}")
        print(f"🔧 SERVICE: Response type: {response_type}")
        return response_text, response_type
    
    async def refresh_session_state(self, user_id: str, session_id: str):
        """Refresh session state from database to ensure we have the latest data"""
        try:
            session = await self.session_service.get_session(
                app_name="Writing Agent",
                user_id=user_id,
                session_id=session_id
            )
            if session:
                print(f"🔧 SERVICE: Session state refreshed - translations: {len(session.state.get('user_translations_en', []))}, current index: {session.state.get('current_part_index', 0)}")
                return session.state
        except Exception as e:
            print(f"🔧 SERVICE: Error refreshing session state: {e}")
        return None

    async def call_agent_async(self, runner, user_id: str, session_id: str, user_input: str):
        """Call the agent asynchronously with the user's query."""
        content = types.Content(role="user", parts=[types.Part(text=user_input)])
        print(
            f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}--- Running Query: {user_input} ---{Colors.RESET}"
        )
        final_response_text = None

        # Display state before processing
        await self.display_state(
            runner.session_service,
            runner.app_name,
            user_id,
            session_id,
            "State BEFORE processing",
        )

        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=content
            ):
                # Process each event and get the final response if available
                response = await self.process_agent_response(event)
                if response:
                    final_response_text = response
        except Exception as e:
            print(f"🔧 SERVICE: Error during agent call: {e}")

        # Display state after processing the message
        await self.display_state(
            runner.session_service,
            runner.app_name,
            user_id,
            session_id,
            "State AFTER processing",
        )

        # Refresh session state to ensure we have the latest data
        await self.refresh_session_state(user_id, session_id)

        # Extract tool feedback if it's a tool response
        response_type = "feedback"  # Default type
        if final_response_text:
            final_response_text, response_type = self.extract_tool_feedback(final_response_text)

        return final_response_text, response_type
    
    async def display_state(
        self, session_service, app_name, user_id, session_id, label="Current State"
    ):
        """Display the current session state in a formatted way."""
        try:
            session = await session_service.get_session(
                app_name=app_name, user_id=user_id, session_id=session_id
            )

            # Format the output with clear sections
            print(f"\n{'-' * 10} {label} {'-' * 10}")

            # Handle the topic and level
            topic = session.state.get("topic", "")
            level = session.state.get("level", "")
            length = session.state.get("length", "")
            print(f"📚 Topic: {topic if topic else 'Unknown'}")
            print(f"📊 Level: {level if level else 'Unknown'}")
            print(f"📏 Length: {length if length else 'Unknown'}")

            # Handle the paragraph
            paragraph_vi = session.state.get("paragraph_vi", "")
            if paragraph_vi:
                print(f"📝 Paragraph (VI): {paragraph_vi[:100]}{'...' if len(paragraph_vi) > 100 else ''}")
            else:
                print("📝 Paragraph (VI): None")

            # Handle sentences
            sentences_vi = session.state.get("sentences_vi", [])
            if sentences_vi:
                print(f"🔤 Sentences (VI): {len(sentences_vi)} sentences")
                for idx, sentence in enumerate(sentences_vi[:3], 1):  # Show first 3 sentences
                    print(f"  {idx}. {sentence}")
                if len(sentences_vi) > 3:
                    print(f"  ... and {len(sentences_vi) - 3} more")
            else:
                print("🔤 Sentences (VI): None")

            # Handle translations and feedbacks
            user_translations = session.state.get("user_translations_en", [])
            feedbacks = session.state.get("feedbacks", [])
            current_index = session.state.get("current_part_index", 0)
            
            print(f"🔄 Current Index: {current_index}")
            print(f"📝 User Translations: {len(user_translations)}")
            print(f"💬 Feedbacks: {len(feedbacks)}")

            # Handle statistics
            statistics = session.state.get("statistics", {})
            if statistics:
                accuracy = statistics.get("accuracy_rate", 0.0)
                print(f"📊 Accuracy Rate: {accuracy:.1%}")

            print("-" * (22 + len(label)))
        except Exception as e:
            print(f"🔧 SERVICE: Error displaying state: {e}")
    
    async def create_session(self, user_id: str, topic: str, level: str, length: str):
        """Create a new writing practice session"""
        print(f"🔧 SERVICE: Creating session for user: {user_id}, topic: {topic}")
        
        try:
            # Create new session first
            session = await self.session_service.create_session(
                app_name="Writing Agent",
                user_id=user_id
            )
            
            # Initialize session state
            session.state = initial_state.copy()
            session.state["topic"] = topic
            session.state["level"] = level
            session.state["length"] = length
            session.state["session_start_time"] = int(time.time())
            
            # Create runner
            runner = Runner(
                agent=writing_agent,
                app_name="Writing Agent",
                session_service=self.session_service
            )
            
            # Kích hoạt agent để tạo đoạn văn
            user_input = f"Bắt đầu bài viết về {topic}, {level}, {length}"
            await self.call_agent_async(runner, user_id, session.id, user_input)
            
            # Lấy thông tin từ trạng thái session sau khi agent đã chạy
            updated_session = await self.session_service.get_session(
                app_name="Writing Agent",
                user_id=user_id,
                session_id=session.id
            )
            
            if not updated_session or not updated_session.state.get("paragraph_vi"):
                raise HTTPException(status_code=500, detail="Không thể tạo đoạn văn. Vui lòng thử lại.")
            
            print(f"🔧 SERVICE: Session created successfully with {len(updated_session.state['sentences_vi'])} sentences")
            
            # Create chat response for the session creation
            chat_response_text = f"Đã tạo bài viết về chủ đề '{topic}' với {len(updated_session.state['sentences_vi'])} câu. Hãy bắt đầu dịch câu đầu tiên: '{updated_session.state['sentences_vi'][0]}'"
            
            return {
                "session_id": session.id,
                "paragraph_vi": updated_session.state["paragraph_vi"],
                "sentences_vi": updated_session.state["sentences_vi"],
                "chat_response": {
                    "response": chat_response_text,
                    "type": "instruction"
                }
            }
            
        except Exception as e:
            print(f"🔧 SERVICE: Error in create_session: {e}")
            raise HTTPException(status_code=500, detail=f"Lỗi khi tạo phiên luyện tập: {str(e)}")
    
    async def process_chat_message(self, user_id: str, session_id: str, message: str):
        """Process a chat message through the AI agent"""
        print(f"🔧 SERVICE: Processing chat message: '{message[:50]}...'")
        
        try:
            # Get runner and session
            runner, current_session_id = await self.get_runner_and_session(user_id, session_id)
            
            # Call the AI agent
            response_text, response_type = await self.call_agent_async(runner, user_id, current_session_id, message)
            
            # Let AI agent determine response type - no hard coding
            return {
                "response": response_text,
                "type": response_type  # Default type, AI agent will determine based on context
            }
            
        except Exception as e:
            print(f"🔧 SERVICE: Error in process_chat_message: {e}")
            raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý tin nhắn: {str(e)}")

# Create service instance
writing_agent_service = WritingAgentService()
