"""Post-extraction schema ASSERTION layer: catches LLM hallucinations.
Pydantic enforces shape; these checks enforce that values are grounded in the source text
and are internally consistent."""
import re

from ..schemas import ExtractedDocument

CENT = 0.02


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def _amount_in_text(amount: float, text: str) -> bool:
    variants = {f"{amount:,.2f}", f"{amount:.2f}"}
    if float(amount).is_integer():
        variants |= {f"{int(amount):,}", str(int(amount))}
    return any(v in text for v in variants)


def assert_extraction(doc: ExtractedDocument, raw_text: str) -> list[str]:
    errors: list[str] = []

    # 1. Grounding: identifiers/amounts must literally appear in the document
    if _norm(doc.po_number) not in _norm(raw_text):
        errors.append(f"hallucination check: PO number {doc.po_number!r} not found in document text")
    if doc.total_cost is not None and not _amount_in_text(doc.total_cost, raw_text):
        errors.append(f"hallucination check: total {doc.total_cost:,.2f} not found in document text")

    # 2. Arithmetic consistency
    for i, li in enumerate(doc.line_items, 1):
        if abs(li.quantity * li.unit_price - li.amount) > CENT:
            errors.append(
                f"line {i} ({li.description!r}): {li.quantity} x {li.unit_price} != {li.amount}"
            )
    if doc.line_items and doc.total_cost is not None:
        lines_sum = round(sum(li.amount for li in doc.line_items), 2)
        base = doc.subtotal if doc.subtotal is not None else lines_sum
        if doc.subtotal is not None and abs(lines_sum - doc.subtotal) > CENT:
            errors.append(f"line items sum {lines_sum:,.2f} != subtotal {doc.subtotal:,.2f}")
        if abs(base + (doc.tax or 0) - doc.total_cost) > CENT:
            errors.append(
                f"subtotal/line sum {base:,.2f} + tax {(doc.tax or 0):,.2f} != total {doc.total_cost:,.2f}"
            )
    return errors
