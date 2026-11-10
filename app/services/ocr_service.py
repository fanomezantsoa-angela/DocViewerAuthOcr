# app/services/ocr_service.py
import io
import os
import re
from statistics import fmean

import pytesseract
from pdf2image import convert_from_bytes, pdfinfo_from_bytes
from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError,
)
from PIL import Image, ImageOps, UnidentifiedImageError

from app.schemas.ocr import OCRResponse

DEFAULT_LANGUAGE = "eng+fra"
ALLOWED_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP", "TIFF", "BMP"}
LANGUAGE_PATTERN = re.compile(r"^[a-z_]{3,10}(\+[a-z_]{3,10})*$")
PDF_DPI = 200
MAX_PDF_PAGES = int(os.getenv("OCR_MAX_PAGES", "10"))
OCR_TIMEOUT_SECONDS = 60


class OCRError(Exception):
    status_code = 500


class OCRInputError(OCRError):
    """The uploaded file or the request options cannot be processed."""

    status_code = 422


class OCRUnavailableError(OCRError):
    """OCR tools are missing on the server."""

    status_code = 503


def is_pdf(content: bytes) -> bool:
    return content.lstrip()[:5] == b"%PDF-"


def validate_language(language: str) -> str:
    if not LANGUAGE_PATTERN.match(language):
        raise OCRInputError("Invalid language. Use codes like 'eng' or 'eng+fra'.")
    try:
        installed = set(pytesseract.get_languages(config=""))
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailableError("Tesseract is not installed on the server.") from exc
    missing = [code for code in language.split("+") if code not in installed]
    if missing:
        raise OCRInputError(f"Language not installed: {', '.join(missing)}")
    return language


def ocr_image_bytes(content: bytes, language: str) -> OCRResponse:
    language = validate_language(language)
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise OCRInputError(
                    "Unsupported image format. Use PNG, JPEG, WebP, TIFF or BMP."
                )
            image.load()
            prepared = ImageOps.exif_transpose(image).convert("L")
    except UnidentifiedImageError as exc:
        raise OCRInputError("The file is not a valid image or PDF.") from exc
    except Image.DecompressionBombError as exc:
        raise OCRInputError("The image is too large to process.") from exc

    text, confidences = _recognize(prepared, language)
    return _build_response([text], confidences, pages=1, language=language)


def ocr_pdf_bytes(content: bytes, language: str) -> OCRResponse:
    language = validate_language(language)
    try:
        total_pages = int(pdfinfo_from_bytes(content)["Pages"])
    except PDFInfoNotInstalledError as exc:
        raise OCRUnavailableError("Poppler is not installed on the server.") from exc
    except (PDFPageCountError, PDFSyntaxError) as exc:
        raise OCRInputError("The file is not a valid PDF.") from exc

    if total_pages > MAX_PDF_PAGES:
        raise OCRInputError(
            f"The PDF has {total_pages} pages; the limit is {MAX_PDF_PAGES}."
        )

    texts: list[str] = []
    confidences: list[float] = []
    # One page at a time keeps memory low on small servers.
    for page_number in range(1, total_pages + 1):
        page_images = convert_from_bytes(
            content,
            dpi=PDF_DPI,
            first_page=page_number,
            last_page=page_number,
            grayscale=True,
        )
        page_text, page_confidences = _recognize(page_images[0], language)
        texts.append(page_text)
        confidences.extend(page_confidences)

    return _build_response(texts, confidences, pages=total_pages, language=language)


def _recognize(image: Image.Image, language: str) -> tuple[str, list[float]]:
    try:
        data = pytesseract.image_to_data(
            image,
            lang=language,
            output_type=pytesseract.Output.DICT,
            timeout=OCR_TIMEOUT_SECONDS,
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailableError("Tesseract is not installed on the server.") from exc
    except RuntimeError as exc:
        # pytesseract raises RuntimeError on timeout and TesseractError on failure.
        raise OCRInputError(f"OCR failed: {exc}") from exc

    lines: dict[tuple[int, int, int], list[str]] = {}
    confidences: list[float] = []
    for index, word in enumerate(data["text"]):
        word = word.strip()
        confidence = float(data["conf"][index])
        if not word or confidence < 0:
            continue
        key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
        lines.setdefault(key, []).append(word)
        confidences.append(confidence)

    output: list[str] = []
    previous_paragraph: tuple[int, int] | None = None
    for (block, paragraph, _line), words in lines.items():
        if previous_paragraph is not None and (block, paragraph) != previous_paragraph:
            output.append("")
        output.append(" ".join(words))
        previous_paragraph = (block, paragraph)
    return "\n".join(output), confidences


def _build_response(
    texts: list[str],
    confidences: list[float],
    pages: int,
    language: str,
) -> OCRResponse:
    mean_confidence = round(fmean(confidences) / 100, 4) if confidences else None
    return OCRResponse(
        text="\n\n".join(text for text in texts if text),
        pages=pages,
        confidence=mean_confidence,
        language=language,
    )
