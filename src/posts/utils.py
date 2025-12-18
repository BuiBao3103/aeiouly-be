import re
from typing import Optional
from src.posts.constants import (
    MIN_TITLE_LENGTH,
    MAX_TITLE_LENGTH,
    MIN_CONTENT_LENGTH
)

def validate_title(title: str) -> tuple[bool, Optional[str]]:
    """
    Validate post title
    Returns: (is_valid, error_message)
    """
    if len(title.strip()) < MIN_TITLE_LENGTH:
        return False, f"Tiêu đề phải có ít nhất {MIN_TITLE_LENGTH} ký tự"
    
    if len(title) > MAX_TITLE_LENGTH:
        return False, f"Tiêu đề không được quá {MAX_TITLE_LENGTH} ký tự"
    
    return True, None

def validate_content(content: str) -> tuple[bool, Optional[str]]:
    """
    Validate post content
    Returns: (is_valid, error_message)
    """
    if len(content.strip()) < MIN_CONTENT_LENGTH:
        return False, f"Nội dung phải có ít nhất {MIN_CONTENT_LENGTH} ký tự"
    
    return True, None

def sanitize_title(title: str) -> str:
    """
    Sanitize post title by removing extra whitespace
    """
    return re.sub(r'\s+', ' ', title.strip())

def sanitize_content(content: str) -> str:
    """
    Sanitize post content by removing extra whitespace
    """
    return re.sub(r'\n\s*\n', '\n\n', content.strip())

def generate_slug(title: str) -> str:
    """
    Generate URL-friendly slug from title
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')

def truncate_content(content: str, max_length: int = 200) -> str:
    """
    Truncate content to specified length
    """
    if len(content) <= max_length:
        return content
    
    truncated = content[:max_length]
    # Try to break at a word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # If we can break at a reasonable point
        truncated = truncated[:last_space]
    
    return truncated + "..."

def extract_mentions(content: str) -> list[str]:
    """
    Extract @mentions from content
    """
    mentions = re.findall(r'@(\w+)', content)
    return list(set(mentions))  # Remove duplicates

def extract_hashtags(content: str) -> list[str]:
    """
    Extract #hashtags from content
    """
    hashtags = re.findall(r'#(\w+)', content)
    return list(set(hashtags))  # Remove duplicates 