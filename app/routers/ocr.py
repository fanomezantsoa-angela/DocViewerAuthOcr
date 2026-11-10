# app/routers/ocr.py
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.schemas.ocr import OCRResponse
from app.services import ocr_service

router = APIRouter(prefix="/ocr", tags=["ocr"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # same limit as the Express upload middleware


@router.post("", response_model=OCRResponse)
def extract_text(
    file: Annotated[UploadFile, File(description="Image (PNG, JPEG, WebP, TIFF, BMP) or PDF")],
    lang: Annotated[
        str,
        Query(description="Tesseract language codes, for example 'eng' or 'eng+fra'"),
    ] = ocr_service.DEFAULT_LANGUAGE,
) -> OCRResponse:
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The file is larger than 10 MB.",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The file is empty.",
        )

    try:
        # Detect PDFs from the content, not from the client-provided content type.
        if ocr_service.is_pdf(content):
            return ocr_service.ocr_pdf_bytes(content, lang)
        return ocr_service.ocr_image_bytes(content, lang)
    except ocr_service.OCRError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
