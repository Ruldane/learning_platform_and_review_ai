from pydantic import BaseModel, Field

MAX_SPOKEN_TEXT = 1200
MAX_TRANSCRIPT = 4000


class VoiceTranscript(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TRANSCRIPT)


class SpeechIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_SPOKEN_TEXT)
