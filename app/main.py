# app/main.py
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import spacy
from fastapi import FastAPI

from app.db.base import Base, engine
from app.db import models
from app.routers import auth, ner


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    app.state.nlp = spacy.load("en_core_web_sm")
    yield


app = FastAPI(title="Auth NER API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(ner.router)
