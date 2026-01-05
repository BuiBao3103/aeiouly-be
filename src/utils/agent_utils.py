"""
Utility functions for AI Agent logging and event processing
"""

from google.genai import types
from google.adk.events import Event, EventActions
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmResponse, LlmRequest
import logging
import time
from typing import Optional, List, Dict, Any, Iterable, Tuple, Callable
import json
import re
import copy
logging.getLogger('google_genai.types').setLevel(logging.ERROR)
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
    
    # Determine event type and build info string
    event_type = "UNKNOWN"
    event_details = []
    
    # Check if this is a transfer event
    if hasattr(event, "transfer_to") and event.transfer_to:
        event_type = "TRANSFER"
        event_details.append(f"→ {event.transfer_to}")
    elif hasattr(event, "agent_transfer") and event.agent_transfer:
        event_type = "TRANSFER"
        if hasattr(event.agent_transfer, "target_agent"):
            event_details.append(f"→ {event.agent_transfer.target_agent}")
    
    # Check for final response
    if event.is_final_response():
        if event_type == "UNKNOWN":
            event_type = "FINAL_RESPONSE"
        else:
            event_details.append("(final response)")
    
    # Check content parts for tool/function calls
    if event.content and event.content.parts:
        for idx, part in enumerate(event.content.parts):
            # Function calls
            if hasattr(part, "function_call") and part.function_call:
                if event_type == "UNKNOWN":
                    event_type = "FUNCTION_CALL"
                func_name = part.function_call.name if hasattr(part.function_call, "name") else "unknown"
                event_details.append(f"function: {func_name}")
                log_func_debug(f"  [{idx}] Function Call: {func_name}")
            
            # Tool calls/responses
            elif hasattr(part, "tool_response") and part.tool_response:
                if event_type == "UNKNOWN":
                    event_type = "TOOL_RESPONSE"
                log_func_debug(f"  [{idx}] Tool Response: {part.tool_response.output}")
            
            # Executable code
            elif hasattr(part, "executable_code") and part.executable_code:
                if event_type == "UNKNOWN":
                    event_type = "CODE_GENERATION"
                code = part.executable_code.code
                log_func_debug(f"  [{idx}] Generated Code:\n```python\n{code}\n```")
            
            # Code execution results
            elif hasattr(part, "code_execution_result") and part.code_execution_result:
                if event_type == "UNKNOWN":
                    event_type = "CODE_EXECUTION"
                outcome = part.code_execution_result.outcome
                output = part.code_execution_result.output
                log_func_debug(f"  [{idx}] Code Execution: {outcome} - Output: {output}")
            
            # Function responses
            elif hasattr(part, "function_response") and part.function_response:
                if event_type == "UNKNOWN":
                    event_type = "FUNCTION_RESPONSE"
                log_func_debug(f"  [{idx}] Function Response: {part.function_response}")
            
            # Text content (only if not final response, as that's handled separately)
            elif hasattr(part, "text") and part.text and not event.is_final_response():
                if event_type == "UNKNOWN":
                    event_type = "TEXT"
                text_content = part.text.strip()
                if not text_content.isspace():
                    # Truncate very long text
                    if len(text_content) > 100:
                        text_content = text_content[:97] + "..."
                    event_details.append(f'text: "{text_content}"')
                    log_func_debug(f"  [{idx}] Text: '{text_content}'")
    
    # If still unknown, check for other attributes
    if event_type == "UNKNOWN":
        # Check for common event attributes
        if hasattr(event, "type"):
            event_type = str(event.type).upper()
        else:
            event_type = "EVENT"
    
    # Build event info string
    event_info = f"[{event_type}] Event ID: {event.id}"
    if event.author:
        event_info += f", Author: {event.author}"
    if event_details:
        event_info += f" | {', '.join(event_details)}"
    
    # Keep concise event summary at INFO so it's visible by default
    log_func_info(event_info)


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


def process_agent_response(event, logger: logging.Logger = None):
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
                
                # Get agent name from event author
                agent_name = event.author if event.author else "unknown"
                
                # Log the final response as a single INFO entry with agent name
                boxed_message = (
                    f"\n{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}"
                    f"╔══ AGENT RESPONSE ({agent_name}) ════════════════════════════\n"
                    f"{Colors.CYAN}{Colors.BOLD}{final_response}{Colors.RESET}\n"
                    f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}"
                    f"╚═════════════════════════════════════════════════════════════"
                    f"{Colors.RESET}\n"
                )
                log_func(boxed_message)
                return final_response
        # Skip logging final response without text content (usually from coordinator)
        # This avoids duplicate logs when coordinator routes to subagents
    
    return None


def extract_tool_response(event) -> Optional[Dict[str, Any]]:
    """
    Extract tool response from agent event.
    
    Args:
        event: Event from agent runner
        
    Returns:
        Tool response dict if found, None otherwise
    """
    if not event or not event.content or not event.content.parts:
        return None
    
    for part in event.content.parts:
        # Check tool_response
        if hasattr(part, "tool_response") and part.tool_response:
            output = part.tool_response.output
            if isinstance(output, dict):
                return output
            elif isinstance(output, str):
                try:
                    import json
                    return json.loads(output)
                except json.JSONDecodeError:
                    pass
        
        # Check function_response (tools are also functions in ADK)
        if hasattr(part, "function_response") and part.function_response:
            func_response = part.function_response
            
            # Debug: log function_response structure
            import logging
            debug_logger = logging.getLogger(__name__)
            debug_logger.debug(f"Function response type: {type(func_response)}")
            debug_logger.debug(f"Function response: {func_response}")
            if hasattr(func_response, "__dict__"):
                debug_logger.debug(f"Function response __dict__: {func_response.__dict__}")
            
            # Try different ways to access the response data
            # Method 1: Direct dict
            if isinstance(func_response, dict):
                return func_response
            
            # Method 2: Check for result attribute
            if hasattr(func_response, "result"):
                result = func_response.result
                if isinstance(result, dict):
                    return result
                elif isinstance(result, str):
                    try:
                        import json
                        parsed = json.loads(result)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass
            
            # Method 3: Check for output attribute
            if hasattr(func_response, "output"):
                output = func_response.output
                if isinstance(output, dict):
                    return output
                elif isinstance(output, str):
                    try:
                        import json
                        parsed = json.loads(output)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass
            
            # Method 4: Check for response attribute
            if hasattr(func_response, "response"):
                response = func_response.response
                if isinstance(response, dict):
                    return response
                elif isinstance(response, str):
                    try:
                        import json
                        parsed = json.loads(response)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass
            
            # Method 5: Try to convert function_response to dict if it has __dict__
            if hasattr(func_response, "__dict__"):
                func_dict = func_response.__dict__
                # Look for common keys that might contain the result
                for key in ["result", "output", "response", "data", "value"]:
                    if key in func_dict:
                        value = func_dict[key]
                        if isinstance(value, dict):
                            return value
                        elif isinstance(value, str):
                            try:
                                import json
                                parsed = json.loads(value)
                                if isinstance(parsed, dict):
                                    return parsed
                            except json.JSONDecodeError:
                                pass
                # If no common key found, return the dict itself if it looks like a result
                if func_dict and not any(k.startswith("_") for k in func_dict.keys()):
                    return func_dict
    
    # Also check if final response text contains JSON with translation_message
    if event.is_final_response() and event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "text") and part.text:
                text = part.text.strip()
                # Try to parse as JSON
                if text.startswith("{") and text.endswith("}"):
                    try:
                        import json
                        parsed = json.loads(text)
                        if isinstance(parsed, dict) and "translation_message" in parsed:
                            return parsed
                    except json.JSONDecodeError:
                        pass
    
    return None


async def call_agent_with_logging(
    runner,
    user_id: str,
    session_id: str,
    query: str,
    logger: logging.Logger = None,
    agent_name: str = None,
    return_tool_response: bool = False
):
    """
    Call agent with comprehensive logging including timing information.
    
    Args:
        runner: Agent runner instance
        user_id: User ID
        session_id: Session ID
        query: User query
        logger: Optional logger instance
        agent_name: Optional agent name (will try to extract from runner if not provided)
        return_tool_response: If True, also return tool response dict
        
    Returns:
        Final response text from agent, or tuple (final_response, tool_response) if return_tool_response=True
    """
    log_func = logger.info if logger else print
    
    # Try to get agent name from runner if not provided
    if not agent_name:
        if hasattr(runner, 'agent') and hasattr(runner.agent, 'name'):
            agent_name = runner.agent.name
        elif hasattr(runner, 'agent_name'):
            agent_name = runner.agent_name
        else:
            agent_name = "unknown"
    
    # Record start time
    start_time = time.time()
    start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
    
    # Create content
    content = types.Content(role="user", parts=[types.Part(text=query)])
    
    # Log the query at INFO for visibility; downgrade to DEBUG if too noisy later
    if logger:
        logger.info(
            f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}"
            f"╔══ RUNNING QUERY ════════════════════════════════════════════\n"
            f"{Colors.CYAN}{Colors.BOLD}{query}{Colors.RESET}\n"
            f"{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}"
            f"╚═════════════════════════════════════════════════════════════"
            f"{Colors.RESET}\n"
        )
        logger.info(
            f"{Colors.BG_MAGENTA}{Colors.WHITE}{Colors.BOLD}"
            f"[AGENT: {agent_name}] Start time: {start_time_str}{Colors.RESET}"
        )
    else:
        print(
            f"\n{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}"
            f"╔══ RUNNING QUERY ════════════════════════════════════════════\n"
            f"{Colors.CYAN}{Colors.BOLD}{query}{Colors.RESET}\n"
            f"{Colors.BG_GREEN}{Colors.BLACK}{Colors.BOLD}"
            f"╚═════════════════════════════════════════════════════════════"
            f"{Colors.RESET}"
        )
        print(
            f"{Colors.BG_MAGENTA}{Colors.WHITE}{Colors.BOLD}"
            f"[AGENT: {agent_name}] Start time: {start_time_str}{Colors.RESET}"
        )
    
    final_response_text = None
    tool_response = None
    
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
            
            # Extract tool response from function_response event (not final response)
            if return_tool_response and not tool_response:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # Check function_response (tools return values are in function_response)
                        if hasattr(part, "function_response") and part.function_response:
                            func_response = part.function_response
                            # Try to get the response as dict
                            if isinstance(func_response, dict):
                                tool_response = func_response
                            elif hasattr(func_response, "result"):
                                result = func_response.result
                                if isinstance(result, dict):
                                    tool_response = result
                            elif hasattr(func_response, "__dict__"):
                                # Try to access the actual return value
                                func_dict = func_response.__dict__
                                # Look for the return value in common attributes
                                for key in ["result", "output", "response", "value", "data"]:
                                    if key in func_dict:
                                        value = func_dict[key]
                                        if isinstance(value, dict):
                                            tool_response = value
                                            break
                            if tool_response and logger:
                                logger.debug(f"Extracted tool response: {tool_response}")
                            break
            
            # Process and extract final response (similar to file mẫu)
            if event.is_final_response():
                if event.content and event.content.parts:
                    # Iterate through all parts to find text parts (skip function_call parts)
                    # This avoids the warning about non-text parts in response
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_response_text = part.text.strip()
                            break  # Use first text part found
                
    except Exception as e:
        # Record end time even on error
        end_time = time.time()
        end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
        duration = end_time - start_time
        
        error_msg = f"Error during agent call: {e}"
        log_func(f"{Colors.BG_RED}{Colors.WHITE}{error_msg}{Colors.RESET}")
        log_func(
            f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD}"
            f"[AGENT: {agent_name}] End time: {end_time_str} | Duration: {duration:.2f}s{Colors.RESET}"
        )
        raise
    
    # Record end time
    end_time = time.time()
    end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
    duration = end_time - start_time
    
    # Log timing information
    log_func(
        f"{Colors.BG_MAGENTA}{Colors.WHITE}{Colors.BOLD}"
        f"[AGENT: {agent_name}] End time: {end_time_str} | Duration: {duration:.2f}s{Colors.RESET}"
    )
    
    if return_tool_response:
        return final_response_text, tool_response
    return final_response_text


def build_agent_query(source: str, message: str) -> str:
    """Construct standardized agent query payload."""
    return f"SOURCE:{source}\nMESSAGE:{message}"


def extract_agent_response_text(
    agent_output: Optional[str],
    preferred_keys: Optional[Iterable[str]] = None,
) -> str:
    """Extract plain text from agent output (handles JSON payloads)."""
    if not agent_output:
        return ""

    text = agent_output.strip()
    if not text:
        return ""

    keys = list(preferred_keys or ("response_text", "evaluation_text", "hint_text"))

    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                for key in keys:
                    value = data.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        except json.JSONDecodeError:
            pass

    return text


def extract_json_from_markdown(text: str) -> Optional[str]:
    """
    Extract JSON from markdown code blocks.
    
    Args:
        text: Text that may contain JSON in markdown code blocks
        
    Returns:
        Extracted JSON string if found, None otherwise
    """
    if not text:
        return None
    
    text = text.strip()
    
    # Try to parse as-is first
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    
    # Try to extract from markdown code blocks
    # Pattern: ```json ... ``` or ``` ... ```
    json_pattern = r'```(?:json)?\s*(.*?)\s*```'
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        json_text = match.group(1).strip()
        try:
            json.loads(json_text)
            return json_text
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in text (between { and })
    json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    match = re.search(json_obj_pattern, text, re.DOTALL)
    if match:
        json_text = match.group(0).strip()
        try:
            json.loads(json_text)
            return json_text
        except json.JSONDecodeError:
            pass
    
    return None


def create_json_extraction_callback(
    fallback_wrapper: Optional[Callable[[str], Dict[str, Any]]] = None
) -> Callable[[CallbackContext, LlmResponse], Optional[LlmResponse]]:
    """
    Create an after_model_callback that extracts JSON from markdown code blocks.
    
    Args:
        fallback_wrapper: Optional function to wrap plain text into JSON dict if JSON extraction fails.
                         Should take text as input and return a dict.
    
    Returns:
        Callback function for after_model_callback
    """
    def after_model_callback(
        callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        """
        Callback to extract JSON from markdown response or wrap plain text into JSON.
        
        Args:
            callback_context: Contains state and context information
            llm_response: The LLM response received
            
        Returns:
            Optional LlmResponse with JSON-formatted text if transformation was needed
        """
        # Skip if response is empty
        if not llm_response or not llm_response.content or not llm_response.content.parts:
            return None
        
        # Extract text from response
        response_text = ""
        for part in llm_response.content.parts:
            if hasattr(part, "text") and part.text:
                response_text += part.text
        
        if not response_text:
            return None
        
        # Check if response is already valid JSON
        try:
            json.loads(response_text.strip())
            # Already valid JSON, no transformation needed
            return None
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown
        extracted_json = extract_json_from_markdown(response_text)
        if extracted_json:
            # Found valid JSON in markdown, use it
            json_response = extracted_json
        elif fallback_wrapper:
            # No JSON found, use fallback wrapper to create JSON from plain text
            wrapped_dict = fallback_wrapper(response_text)
            json_response = json.dumps(wrapped_dict, ensure_ascii=False)
        else:
            # No JSON and no fallback, return None (no transformation)
            return None
        
        # Create modified response
        modified_parts = [copy.deepcopy(part) for part in llm_response.content.parts]
        for i, part in enumerate(modified_parts):
            if hasattr(part, "text") and part.text:
                modified_parts[i].text = json_response
                break
        
        return LlmResponse(content=types.Content(role="model", parts=modified_parts))
    
    return after_model_callback


async def get_agent_state(
    session_service,
    app_name: str,
    user_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """Fetch agent session state dictionary."""
    agent_session = await session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    return (agent_session.state or {}) if agent_session else {}


async def log_session_state(session_service, app_name: str, user_id: str, session_id: str, logger: logging.Logger = None):
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
        session = await session_service.get_session(
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


async def update_session_state(
    session_service,
    app_name: str,
    user_id: str,
    session_id: str,
    state_delta: Dict[str, Any],
    author: str = "system",
    invocation_id_prefix: str = "state_update",
    logger: logging.Logger = None
) -> Optional[Any]:
    """
    Update session state using append_event (correct ADK way).
    
    This function properly updates state by creating an Event with state_delta
    and appending it to the session, rather than directly modifying state.
    
    Args:
        session_service: Session service instance (DatabaseSessionService or InMemorySessionService)
        app_name: Application name
        user_id: User ID
        session_id: Session ID
        state_delta: Dictionary of state fields to update (only changed fields)
        author: Author of the event (default: "system")
        invocation_id_prefix: Prefix for invocation_id (default: "state_update")
        logger: Optional logger instance
        
    Returns:
        Updated session object, or None if error occurred
        
    Example:
        await update_session_state(
            session_service=self.session_service,
            app_name="WritingPractice",
            user_id=str(user_id),
            session_id=str(session_id),
            state_delta={
                "current_sentence_index": 1,
                "current_vietnamese_sentence": "Câu mới"
            },
            author="system",
            invocation_id_prefix="skip_sentence"
        )
    """
    log_func = logger.error if logger else print
    
    try:
        # Get current session
        agent_session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        # Create event with state delta
        event = Event(
            invocation_id=f"{invocation_id_prefix}_{int(time.time())}",
            author=author,
            actions=EventActions(state_delta=state_delta),
            timestamp=time.time()
        )
        
        # Append event to update state
        await session_service.append_event(agent_session, event)
        
        # Return updated session
        return await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        
    except Exception as e:
        log_func(f"Error updating session state: {e}")
        return None
