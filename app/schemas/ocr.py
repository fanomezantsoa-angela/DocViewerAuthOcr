# app/schemas/ocr.py
from pydantic import BaseModel, Field


class OCRResponse(BaseModel):
    text: str
    pages: int = Field(ge=1)
    # Mean word confidence between 0 and 1, or null when no text was found.
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    language: str
