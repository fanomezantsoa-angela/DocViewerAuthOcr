import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import spacy
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import ner


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.nlp = spacy.load("en_core_web_sm")
    yield


app = FastAPI(title="NER Extraction API", lifespan=lifespan)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin] if frontend_origin != "*" else ["*"],
    allow_credentials=frontend_origin != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ner.router)
