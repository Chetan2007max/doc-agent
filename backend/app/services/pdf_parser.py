"""PDF -> text. Text layer first (PyMuPDF), OCR fallback for scanned documents."""
import re
import unicodedata

import pymupdf as fitz  # PyMuPDF

MIN_CHARS = 40
MAX_CHARS = 60_000


class ParseError(Exception):
    pass


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\u00a0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:MAX_CHARS]


def extract_text(path: str) -> tuple[str, str]:
    """Returns (text, method) where method is 'text_layer' or 'ocr'."""
    try:
        pdf = fitz.open(path)
    except Exception as e:  # corrupt / encrypted / not a pdf
        raise ParseError(f"Unreadable PDF: {e}")
    if pdf.is_encrypted:
        raise ParseError("PDF is password protected")
    if pdf.page_count == 0:
        raise ParseError("PDF has no pages")

    text = _clean("\n".join(page.get_text("text") for page in pdf))
    if len(text) >= MIN_CHARS:
        return text, "text_layer"

    # Edge case: scanned / image-only PDF -> OCR fallback
    try:
        import pytesseract
        from PIL import Image

        parts = []
        for page in pdf:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            parts.append(pytesseract.image_to_string(img))
        text = _clean("\n".join(parts))
    except Exception as e:
        raise ParseError(
            "No text layer found (likely a scanned PDF) and OCR is unavailable: "
            f"{type(e).__name__}. Install Tesseract + pytesseract to enable OCR fallback."
        )
    if len(text) < MIN_CHARS:
        raise ParseError("OCR produced too little text; document may be blank or illegible")
    return text, "ocr"
