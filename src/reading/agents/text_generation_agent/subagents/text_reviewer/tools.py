"""
Tools for Text Reviewer Agent

This module provides tools for checking word count and controlling loop exit.
"""

from typing import Any, Dict
import re

from google.adk.tools.tool_context import ToolContext


def count_words(text: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool to count words in the provided text and check if it meets the target word count (±20%).
    Updates review_status in the state based on word count requirements.

    Args:
        text: The text to analyze for word count
        tool_context: Context for accessing and updating session state

    Returns:
        Dict[str, Any]: Dictionary containing:
            - result: 'fail' or 'pass'
            - word_count: number of words in text
            - target_word_count: target word count
            - min_words: minimum acceptable words (target - 20%)
            - max_words: maximum acceptable words (target + 20%)
            - message: feedback message about the word count
    """
    # Count words using regex
    words = re.findall(r'\b\w+\b', text.lower())
    word_count = len(words)
    
    # Get target word count from state
    state = tool_context.state or {}
    target_word_count = state.get("target_word_count", 0)
    
    if target_word_count == 0:
        tool_context.state["review_status"] = "fail"
        return {
            "result": "fail",
            "word_count": word_count,
            "message": "Target word count not found in state.",
        }
    
    # Calculate acceptable range (±20%)
    min_words = int(target_word_count * 0.8)
    max_words = int(target_word_count * 1.2)
    
    if word_count < min_words:
        words_needed = min_words - word_count
        tool_context.state["review_status"] = "fail"
        return {
            "result": "fail",
            "word_count": word_count,
            "target_word_count": target_word_count,
            "min_words": min_words,
            "max_words": max_words,
            "words_needed": words_needed,
            "message": f"Text is too short. Current: {word_count} words. Need at least {min_words} words (target: {target_word_count} ±20%). Add approximately {words_needed} more words.",
        }
    elif word_count > max_words:
        words_to_remove = word_count - max_words
        tool_context.state["review_status"] = "fail"
        return {
            "result": "fail",
            "word_count": word_count,
            "target_word_count": target_word_count,
            "min_words": min_words,
            "max_words": max_words,
            "words_to_remove": words_to_remove,
            "message": f"Text is too long. Current: {word_count} words. Maximum allowed: {max_words} words (target: {target_word_count} ±20%). Remove approximately {words_to_remove} words.",
        }
    else:
        tool_context.state["review_status"] = "pass"
        return {
            "result": "pass",
            "word_count": word_count,
            "target_word_count": target_word_count,
            "min_words": min_words,
            "max_words": max_words,
            "message": f"Word count is acceptable ({word_count} words, target: {target_word_count} ±20%).",
        }


def exit_loop(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Call this function ONLY when the text meets all quality requirements,
    signaling the iterative process should end.

    Args:
        tool_context: Context for tool execution

    Returns:
        Empty dictionary
    """
    tool_context.actions.escalate = True
    return {}

