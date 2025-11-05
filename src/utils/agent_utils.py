"""
Utility functions for AI Agent logging and event processing
"""

from google.genai import types
import logging

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


def log_event(event, logger: logging.Logger = None):
    """
    Log event information for debugging loading and integration.
    
    Args:
        event: Event from agent runner
        logger: Optional logger instance, defaults to print if None
    """
    log_func_info = logger.info if logger else print
    log_func_debug = (logger.debug if logger else (lambda *_args, **_kwargs: None))
    
    # Basic event info
    event_info = f"Event ID: {event.id}"
    if event.author:
        event_info += f", Author: {event.author}"
    # Keep concise event summary at INFO so it's visible by default
    log_func_info(event_info)
    
    # Check for specific parts
    if event.content and event.content.parts:
        for idx, part in enumerate(event.content.parts):
            # Tool calls
            if hasattr(part, "tool_response") and part.tool_response:
                log_func_debug(f"  [{idx}] Tool Response: {part.tool_response.output}")
            
            # Executable code
            elif hasattr(part, "executable_code") and part.executable_code:
                code = part.executable_code.code
                log_func_debug(f"  [{idx}] Generated Code:\n```python\n{code}\n```")
            
            # Code execution results
            elif hasattr(part, "code_execution_result") and part.code_execution_result:
                outcome = part.code_execution_result.outcome
                output = part.code_execution_result.output
                log_func_debug(f"  [{idx}] Code Execution: {outcome} - Output: {output}")
            
            # Text content
            elif hasattr(part, "text") and part.text:
                text_content = part.text.strip()
                if not text_content.isspace():
                    # Truncate very long text
                    if len(text_content) > 200:
                        text_content = text_content[:197] + "..."
                    log_func_debug(f"  [{idx}] Text: '{text_content}'")
            
            # Function calls
            elif hasattr(part, "function_call") and part.function_call:
                func_name = part.function_call.name if hasattr(part.function_call, "name") else "unknown"
                log_func_debug(f"  [{idx}] Function Call: {func_name}")
            
            # Function responses
            elif hasattr(part, "function_response") and part.function_response:
                log_func_debug(f"  [{idx}] Function Response: {part.function_response}")


def log_agent_transfer(event, logger: logging.Logger = None):
    """
    Log agent transfer events (when sub-agents are called).
    
    Args:
        event: Event from agent runner
        logger: Optional logger instance, defaults to print if None
    """
    if event.author and event.author != "unknown":
        # Option A: suppress transfer log at INFO; emit at DEBUG only
        if logger:
            logger.debug(
                f"Event from agent: {event.author}, event id: {event.id}"
            )


async def process_agent_response(event, logger: logging.Logger = None):
    """
    Process and extract final response from agent events.
    
    Args:
        event: Event from agent runner
        logger: Optional logger instance
        
    Returns:
        Final response text if available, None otherwise
    """
    log_func = logger.info if logger else print
    
    # Check for final response
    if event.is_final_response():
        if event.content and event.content.parts:
            first_part = event.content.parts[0]
            if hasattr(first_part, "text") and first_part.text:
                final_response = first_part.text.strip()
                
                # Log the final response as a single INFO entry (Option D)
                boxed_message = (
                    f"\n{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}"
                    f"╔══ AGENT RESPONSE ═════════════════════════════════════════\n"
                    f"{Colors.CYAN}{Colors.BOLD}{final_response}{Colors.RESET}\n"
                    f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}"
                    f"╚═════════════════════════════════════════════════════════════"
                    f"{Colors.RESET}\n"
                )
                log_func(boxed_message)
                return final_response
        else:
            log_func(
                f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD}"
                f"==> Final Agent Response: [No text content in final event]"
                f"{Colors.RESET}"
            )
    
    return None


async def call_agent_with_logging(
    runner,
    user_id: str,
    session_id: str,
    query: str,
    logger: logging.Logger = None
):
    """
    Call agent with comprehensive logging.
    
    Args:
        runner: Agent runner instance
        user_id: User ID
        session_id: Session ID
        query: User query
        logger: Optional logger instance
        
    Returns:
        Final response text from agent
    """
    log_func = logger.info if logger else print
    
    # Create content
    content = types.Content(role="user", parts=[types.Part(text=query)])
    
    # Log the query at INFO for visibility; downgrade to DEBUG if too noisy later
    if logger:
        logger.info(
            f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}"
            f"--- Running Query: {query} ---"
            f"{Colors.RESET}"
        )
    else:
        print(
            f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}"
            f"--- Running Query: {query} ---"
            f"{Colors.RESET}"
        )
    
    final_response_text = None
    
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            # Log agent transfers
            log_agent_transfer(event, logger)
            
            # Log event details
            log_event(event, logger)
            
            # Process and extract final response
            response = await process_agent_response(event, logger)
            if response:
                final_response_text = response
                
    except Exception as e:
        error_msg = f"Error during agent call: {e}"
        log_func(f"{Colors.BG_RED}{Colors.WHITE}{error_msg}{Colors.RESET}")
        raise
    
    return final_response_text


def log_session_state(session_service, app_name: str, user_id: str, session_id: str, logger: logging.Logger = None):
    """
    Log the current session state for debugging.
    
    Args:
        session_service: Session service instance
        app_name: Application name
        user_id: User ID
        session_id: Session ID
        logger: Optional logger instance
    """
    log_func = logger.info if logger else print
    
    try:
        import asyncio
        
        # Handle both sync and async session service
        try:
            session = asyncio.run(
                session_service.get_session(
                    app_name=app_name,
                    user_id=user_id,
                    session_id=session_id
                )
            )
        except (TypeError, RuntimeError):
            # If session service is synchronous
            session = session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
        
        log_func(f"\n{'-' * 10} Session State {'-' * 10}")
        
        # Log state keys and values
        if hasattr(session, 'state') and isinstance(session.state, dict):
            for key, value in session.state.items():
                # Truncate long values
                if isinstance(value, str) and len(value) > 100:
                    value = value[:97] + "..."
                log_func(f"  {key}: {value}")
        else:
            log_func(f"  State: {session.state}")
        
        log_func("-" * 40)
        
    except Exception as e:
        log_func(f"Error logging session state: {e}")

