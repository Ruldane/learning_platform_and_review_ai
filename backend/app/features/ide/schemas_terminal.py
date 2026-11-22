from pydantic import BaseModel, Field

from app.providers.sandbox.base import MAX_INPUT_CHUNK_BYTES


class TerminalStarted(BaseModel):
    id: str


class TerminalInput(BaseModel):
    data: str = Field(min_length=1, max_length=MAX_INPUT_CHUNK_BYTES)
