# app/schemas/ner.py
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class NERRequest(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Entity(BaseModel):
    text: str
    label: str
    start: int
    end: int
    confidence: float = Field(ge=0.0, le=1.0)
    context: str | None = None


class NERResponse(BaseModel):
    entities: list[Entity]
