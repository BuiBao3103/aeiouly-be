"""Schemas for Speaking module"""
from pydantic import BaseModel, Field


class SpeechToTextResponse(BaseModel):
    """Response schema for speech-to-text conversion"""
    text: str = Field(..., description="Transcribed text from audio")


class SpeechToTextRequest(BaseModel):
    """Request schema for speech-to-text (optional metadata)"""
    language_code: str = Field(default="en-US", description="Language code (default: en-US)")
    sample_rate_hertz: int = Field(default=16000, description="Sample rate in Hz (default: 16000)")
    encoding: str = Field(default="LINEAR16", description="Audio encoding (default: LINEAR16)")

