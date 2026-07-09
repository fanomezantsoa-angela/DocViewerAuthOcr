# app/routers/ner.py
from fastapi import APIRouter, Depends, Request
from spacy.language import Language

from app.core.security import get_current_user
from app.db.models import User
from app.schemas.ner import NERRequest, NERResponse
from app.services.ner_service import analyze_text


router = APIRouter(prefix="/ner", tags=["ner"])


def get_nlp(request: Request) -> Language:
    return request.app.state.nlp


@router.post("/analyze", response_model=NERResponse)
def analyze(
    payload: NERRequest,
    current_user: User = Depends(get_current_user),
    nlp: Language = Depends(get_nlp),
) -> NERResponse:
    return analyze_text(nlp, payload.text)
