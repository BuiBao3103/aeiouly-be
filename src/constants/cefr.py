"""
CEFR (Common European Framework of Reference) Level Definitions
Optimized for AI Agent.
"""

from enum import Enum
from typing import List

class CEFRLevel(str, Enum):
    """CEFR Language Proficiency Levels"""
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"

class CEFRLevelInfo:
    """Detailed information about CEFR levels"""
    
    # Compact descriptions
    DESCRIPTIONS = {
        CEFRLevel.A1: "Beginner",
        CEFRLevel.A2: "Elementary", 
        CEFRLevel.B1: "Intermediate",
        CEFRLevel.B2: "Upper-Intermediate",
        CEFRLevel.C1: "Advanced",
        CEFRLevel.C2: "Mastery"
    }
    
    # Grammar complexity (compact)
    GRAMMAR_COMPLEXITY = {
        CEFRLevel.A1: "Simple present/past/future",
        CEFRLevel.A2: "Continuous tenses, basic conditionals",
        CEFRLevel.B1: "Passive voice, reported speech, relative clauses",
        CEFRLevel.B2: "Mixed conditionals, advanced structures",
        CEFRLevel.C1: "Inversion, cleft sentences, subjunctive",
        CEFRLevel.C2: "All structures with near-native precision",
    }
    
    # Vocabulary complexity (compact)
    VOCABULARY_COMPLEXITY = {
        CEFRLevel.A1: "Basic everyday words",
        CEFRLevel.A2: "Common phrases, simple idioms",
        CEFRLevel.B1: "Intermediate vocabulary, basic professional terms",
        CEFRLevel.B2: "Advanced vocabulary, specialized terms",
        CEFRLevel.C1: "Sophisticated vocabulary, academic language",
        CEFRLevel.C2: "Near-native range, subtle nuances",
    }

def get_cefr_levels() -> List[CEFRLevel]:
    """Get all CEFR levels in order"""
    return [CEFRLevel.A1, CEFRLevel.A2, CEFRLevel.B1, CEFRLevel.B2, CEFRLevel.C1, CEFRLevel.C2]

def get_level_description(level: CEFRLevel) -> str:
    """Get description for a CEFR level"""
    return CEFRLevelInfo.DESCRIPTIONS.get(level, "")

def get_grammar_complexity(level: CEFRLevel) -> str:
    """Get grammar complexity description for a CEFR level"""
    return CEFRLevelInfo.GRAMMAR_COMPLEXITY.get(level, "")

def get_vocabulary_complexity(level: CEFRLevel) -> str:
    """Get vocabulary complexity description for a CEFR level"""
    return CEFRLevelInfo.VOCABULARY_COMPLEXITY.get(level, "")

def is_valid_cefr_level(level: str) -> bool:
    """Check if a string is a valid CEFR level"""
    try:
        CEFRLevel(level)
        return True
    except ValueError:
        return False

def get_level_order(level: CEFRLevel) -> int:
    """Get numeric order of CEFR level (A1=1, A2=2, ..., C2=6)"""
    order = {
        CEFRLevel.A1: 1, CEFRLevel.A2: 2, CEFRLevel.B1: 3,
        CEFRLevel.B2: 4, CEFRLevel.C1: 5, CEFRLevel.C2: 6
    }
    return order.get(level, 0)

def compare_levels(level1: CEFRLevel, level2: CEFRLevel) -> int:
    """Compare two CEFR levels. Returns -1 if level1 < level2, 0 if equal, 1 if level1 > level2"""
    order1 = get_level_order(level1)
    order2 = get_level_order(level2)
    
    if order1 < order2:
        return -1
    elif order1 > order2:
        return 1
    else:
        return 0

def get_cefr_definitions_string() -> str:
    """Return compact CEFR definitions for AI prompts"""
    lines = ["CEFR LEVELS:\n"]
    
    for level in CEFRLevel:
        desc = CEFRLevelInfo.DESCRIPTIONS.get(level, "")
        grammar = CEFRLevelInfo.GRAMMAR_COMPLEXITY.get(level, "")
        vocab = CEFRLevelInfo.VOCABULARY_COMPLEXITY.get(level, "")
        
        lines.append(f"{level.value} ({desc}):")
        lines.append(f"  Grammar: {grammar}")
        lines.append(f"  Vocabulary: {vocab}\n")
    
    return "\n".join(lines)

