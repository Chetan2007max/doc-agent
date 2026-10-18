"""Deterministic extraction: temperature 0 + JSON-schema-constrained output, then Pydantic
validation + grounding assertions. Retries with error feedback, then falls back to a
rule-based extractor, then routes to a human with the full audit trail."""
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from pydantic import ValidationError

from ..config import settings
from ..schemas import ExtractedDocument
from .validator import assert_extraction

SYSTEM_PROMPT = (
    "You extract structured data from logistics documents (freight invoices and bills of lading). "
    "Rules: copy values exactly as printed; NEVER infer, estimate or compute values; use null for "
    "anything not printed; amounts are plain numbers (no currency symbols or thousands separators); "
    "dates are ISO YYYY-MM-DD; weight is in kilograms (convert lbs x 0.453592); doc_type is INVOICE "
    "for freight invoices and BOL for bills of lading."
)


@dataclass
class ExtractionResult:
    data: Optional[ExtractedDocument]
    raw: Optional[dict]
    method: str
    errors: list[str]
    trail: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------- Gemini (schema-enforced)
def _gemini(text: str, feedback: Optional[list[str]]) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = f"Document text:\n<<<\n{text}\n>>>"
    if feedback:
        prompt += (
            "\n\nYour previous output failed validation:\n- " + "\n- ".join(feedback)
            + "\nRe-extract using ONLY values printed in the document."
        )
    resp = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            response_mime_type="application/json",
            response_schema=ExtractedDocument,   # JSON-schema enforcement
        ),
    )
    return resp.text


# ---------------------------------------------------------------- Rule-based fallback
def _num(s: str) -> float:
    return float(s.replace(",", "").replace("$", "").strip())


def _find(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else None


def _heuristic(text: str, feedback: Optional[list[str]] = None) -> dict:
    is_bol = "bill of lading" in text.lower()
    weight = None
    m = re.search(r"Total\s*Weight\s*:?\s*([\d,]+(?:\.\d+)?)\s*(kgs?|lbs?)?", text, re.I)
    if m:
        weight = _num(m.group(1))
        if (m.group(2) or "").lower().startswith("lb"):
            weight = round(weight * 0.453592, 2)
    totals = re.findall(r"(?<![A-Za-z])Total\s*(?:Due|Amount|Cost|Charges)?\s*:?\s*\$?\s*([\d,]+\.\d{2})", text, re.I)
    items = []
    for m in re.finditer(
        r"^(.+?)\s+(\d+(?:\.\d+)?)\s+\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})\s*$", text, re.M
    ):
        items.append({"description": m.group(1).strip(), "quantity": float(m.group(2)),
                      "unit_price": _num(m.group(3)), "amount": _num(m.group(4))})
    sub = _find(r"Subtotal\s*:?\s*\$?\s*([\d,]+\.\d{2})", text)
    tax = _find(r"Tax[^\n:]*:?\s*\$?\s*([\d,]+\.\d{2})", text)
    return {
        "doc_type": "BOL" if is_bol else "INVOICE",
        "po_number": _find(r"\b(?:PO|P\.O\.|Purchase Order)(?:\s*(?:Number|No\.?|#))?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{3,})", text),
        "invoice_number": _find(r"Invoice\s*(?:Number|No\.?|#)\s*:?\s*([A-Z0-9\-]+)", text),
        "carrier_name": _find(r"Carrier(?:\s*Name)?\s*:\s*(.+)", text),
        "line_items": items,
        "subtotal": _num(sub) if sub else None,
        "tax": _num(tax) if tax else None,
        "total_cost": _num(totals[-1]) if totals else None,
        "total_weight": weight,
        "delivery_date": _find(r"Delivery\s*Date\s*:?\s*(\d{4}-\d{2}-\d{2})", text),
    }


# ---------------------------------------------------------------- Orchestration
def _provider_chain() -> list[tuple[str, Callable, int]]:
    chain = []
    use_gemini = settings.llm_provider in ("auto", "gemini") and settings.gemini_api_key
    if use_gemini:
        chain.append(("gemini", _gemini, settings.max_llm_retries + 1))
    chain.append(("rule_based", _heuristic, 1))
    return chain


def extract_document(text: str) -> ExtractionResult:
    trail: list[dict] = []
    best: Optional[ExtractedDocument] = None
    last_raw: Optional[dict] = None
    errors: list[str] = []

    for name, fn, tries in _provider_chain():
        feedback = None
        for attempt in range(1, tries + 1):
            doc, raw = None, None
            try:
                out: Any = fn(text, feedback)
                if isinstance(out, str):
                    doc = ExtractedDocument.model_validate_json(out)
                else:
                    raw = out
                    doc = ExtractedDocument.model_validate(out)
                raw = doc.model_dump()
                errors = assert_extraction(doc, text)
                best = doc
            except ValidationError as e:
                errors = [f"schema: {'.'.join(map(str, x['loc'])) or 'root'}: {x['msg']}" for x in e.errors()]
            except Exception as e:
                errors = [f"{name} call failed: {type(e).__name__}: {e}"]
                if name == "gemini" and attempt < tries:
                    time.sleep(2 * attempt)  # back off on 503/429
            last_raw = raw or last_raw
            trail.append({"provider": name, "attempt": attempt, "ok": not errors, "errors": errors})
            if not errors:
                return ExtractionResult(doc, raw, name, [], trail)
            feedback = errors
    return ExtractionResult(best, last_raw, "failed", errors, trail)
