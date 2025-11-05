"""
Utilities for listening module
"""
import re
import json
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

@dataclass
class SRTSubtitle:
    index: int
    start_time: float
    end_time: float
    text: str

class SRTParser:
    """Parser for SRT subtitle files"""
    
    @staticmethod
    def parse_srt_content(srt_content: str) -> List[SRTSubtitle]:
        """
        Parse SRT content and extract subtitles with timing
        """
        subtitles = []
        
        # Split by double newlines to get individual subtitle blocks
        blocks = re.split(r'\n\s*\n', srt_content.strip())
        
        for block in blocks:
            if not block.strip():
                continue
                
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
                
            try:
                # First line is index
                index = int(lines[0])
                
                # Second line is timing
                timing_line = lines[1]
                start_time, end_time = SRTParser._parse_timing(timing_line)
                
                # Remaining lines are text - join with space and collapse whitespace
                raw_text = ' '.join(lines[2:]).strip()
                text = re.sub(r'\s+', ' ', raw_text)
                
                subtitles.append(SRTSubtitle(
                    index=index,
                    start_time=start_time,
                    end_time=end_time,
                    text=text
                ))
                
            except (ValueError, IndexError) as e:
                print(f"Error parsing subtitle block: {e}")
                continue
                
        return subtitles
    
    @staticmethod
    def _parse_timing(timing_line: str) -> Tuple[float, float]:
        """
        Parse timing line like "00:00:01,000 --> 00:00:04,000"
        Returns (start_time, end_time) in seconds
        """
        # Remove arrow and split
        parts = timing_line.replace(' --> ', ' ').split()
        if len(parts) != 2:
            raise ValueError(f"Invalid timing format: {timing_line}")
            
        start_time = SRTParser._time_to_seconds(parts[0])
        end_time = SRTParser._time_to_seconds(parts[1])
        
        return start_time, end_time
    
    @staticmethod
    def _time_to_seconds(time_str: str) -> float:
        """
        Convert time string like "00:00:01,000" to seconds
        """
        # Replace comma with dot for milliseconds
        time_str = time_str.replace(',', '.')
        
        # Parse HH:MM:SS.mmm
        parts = time_str.split(':')
        if len(parts) != 3:
            raise ValueError(f"Invalid time format: {time_str}")
            
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        
        return hours * 3600 + minutes * 60 + seconds

def _strip_speaker_label(text: str) -> str:
    """Remove leading speaker labels like 'Feifei:' or 'A:' if present."""
    if not text:
        return ""
    candidate = text.strip()
    patterns = [
        # Names like Feifei:, Rob:, "BBC Host:", including spaces, dots, hyphens, apostrophes
        r"^\s*[\[\(]?\s*[A-Za-z][A-Za-z .'-]{0,30}\s*[\]\)]?\s*:\s*",
        # Single-letter speakers like A:, B:, C:
        r"^\s*[A-Z]\s*:\s*",
    ]
    for pat in patterns:
        if re.match(pat, candidate):
            candidate = re.sub(pat, '', candidate).lstrip()
            break
    return candidate or text


def sanitize_subtitle_text(text: str) -> str:
    """Normalize subtitle text: strip speaker labels and collapse whitespace."""
    if not text:
        return ""
    # First, remove leading speaker labels
    no_speaker = _strip_speaker_label(text)
    # Then collapse whitespace
    return re.sub(r'\s+', ' ', no_speaker.strip())

def is_non_speech_subtitle(text: str) -> bool:
    """Return True if the subtitle is a non-speech annotation like (Silence)."""
    if not text:
        return True
    stripped = text.strip()
    if stripped.startswith("(") and stripped.endswith(")"):
        inner = stripped[1:-1].strip().lower()
        non_speech_tokens = {
            "silence",
            "laughter",
            "applause",
            "music",
            "crowd cheering",
            "cheering",
            "clapping",
            "gasps",
            "sighs",
            "chuckles",
        }
        return inner in non_speech_tokens
    return False

class TextNormalizer:
    """Normalize text for comparison"""
    
    # Contraction mapping
    CONTRACTIONS = {
        "i'm": "i am", "you're": "you are", "he's": "he is", "she's": "she is",
        "it's": "it is", "we're": "we are", "they're": "they are",
        "i'll": "i will", "you'll": "you will", "he'll": "he will",
        "she'll": "she will", "we'll": "we will", "they'll": "they will",
        "i've": "i have", "you've": "you have", "he's": "he has",
        "she's": "she has", "we've": "we have", "they've": "they have",
        "i'd": "i would", "you'd": "you would", "he'd": "he would",
        "she'd": "she would", "we'd": "we would", "they'd": "they would",
        "won't": "will not", "can't": "cannot", "don't": "do not",
        "doesn't": "does not", "didn't": "did not", "haven't": "have not",
        "hasn't": "has not", "hadn't": "had not", "isn't": "is not",
        "aren't": "are not", "wasn't": "was not", "weren't": "were not"
    }
    
    @classmethod
    def normalize(cls, text: str) -> str:
        """
        Normalize text for comparison:
        - Convert to lowercase
        - Replace numbers with words
        - Expand contractions
        - Remove extra punctuation
        - Remove extra spaces
        """
        if not text:
            return ""
            
        # Convert to lowercase
        normalized = text.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Expand contractions
        for contraction, expansion in cls.CONTRACTIONS.items():
            normalized = re.sub(r'\b' + re.escape(contraction) + r'\b', expansion, normalized)
        
        # Remove extra punctuation (keep basic punctuation)
        normalized = re.sub(r'[^\w\s.,!?]', '', normalized)
        
        # Remove multiple punctuation
        normalized = re.sub(r'[.,!?]+', lambda m: m.group(0)[0], normalized)
        
        # Final cleanup
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
