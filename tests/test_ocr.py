# tests/test_ocr.py
import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.routers import ocr

# A small app with only the OCR router, so tests do not need the spaCy model.
app = FastAPI()
app.include_router(ocr.router, prefix="/api")
client = TestClient(app)

SAMPLE_TEXT = "Invoice 2026 Paris"


def make_image(text: str = SAMPLE_TEXT) -> Image.Image:
    image = Image.new("RGB", (900, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 60), text, fill="black", font=ImageFont.load_default(size=64))
    return image


def to_bytes(image: Image.Image, fmt: str) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, fmt)
    return buffer.getvalue()


def post(content: bytes, filename: str, content_type: str, **params):
    return client.post(
        "/api/ocr",
        files={"file": (filename, content, content_type)},
        params=params,
    )


def test_png_image_is_read():
    response = post(to_bytes(make_image(), "PNG"), "scan.png", "image/png", lang="eng")
    assert response.status_code == 200
    body = response.json()
    assert "invoice" in body["text"].lower()
    assert "2026" in body["text"]
    assert body["pages"] == 1
    assert 0 < body["confidence"] <= 1
    assert body["language"] == "eng"


def test_pdf_is_read_even_with_wrong_content_type():
    pdf = to_bytes(make_image(), "PDF")
    response = post(pdf, "scan.pdf", "application/octet-stream", lang="eng")
    assert response.status_code == 200
    body = response.json()
    assert "invoice" in body["text"].lower()
    assert body["pages"] == 1


def test_default_language_is_english_and_french():
    response = post(to_bytes(make_image(), "PNG"), "scan.png", "image/png")
    assert response.status_code == 200
    assert response.json()["language"] == "eng+fra"


def test_blank_image_returns_empty_text():
    blank = Image.new("RGB", (400, 200), "white")
    response = post(to_bytes(blank, "PNG"), "blank.png", "image/png", lang="eng")
    assert response.status_code == 200
    assert response.json()["text"] == ""
    assert response.json()["confidence"] is None


def test_invalid_file_is_rejected():
    response = post(b"not an image", "notes.txt", "text/plain", lang="eng")
    assert response.status_code == 422


def test_empty_file_is_rejected():
    response = post(b"", "empty.png", "image/png", lang="eng")
    assert response.status_code == 422


def test_unknown_language_is_rejected():
    response = post(to_bytes(make_image(), "PNG"), "scan.png", "image/png", lang="zzz")
    assert response.status_code == 422
    assert "zzz" in response.json()["detail"]


def test_malformed_language_is_rejected():
    response = post(to_bytes(make_image(), "PNG"), "scan.png", "image/png", lang="eng;rm")
    assert response.status_code == 422


def test_large_file_is_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ocr, "MAX_UPLOAD_BYTES", 100)
    response = post(b"x" * 101, "big.png", "image/png", lang="eng")
    assert response.status_code == 413
