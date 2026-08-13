# app/services/ner_service.py
from spacy.language import Language

from app.schemas.ner import Entity, NERResponse


def analyze_text(nlp: Language, text: str) -> NERResponse:
    doc = nlp(text)
    entities = [
        Entity(
            text=ent.text,
            label=ent.label_,
            start=ent.start_char,
            end=ent.end_char,
            confidence=1.0,
            context=doc.text[ent.start_char - 30 : ent.end_char + 30] if ent.start_char >= 30 else doc.text[: ent.end_char + 30],
        )
        for ent in doc.ents
    ]
    return NERResponse(entities=entities)
