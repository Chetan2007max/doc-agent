"""Autonomous workflow: parse -> extract -> assert -> reconcile -> route."""
from sqlalchemy.orm import Session

from ..models import DocStatus, Document
from .extractor import extract_document
from .pdf_parser import ParseError, extract_text
from .reconciler import reconcile


def process_document(db: Session, doc: Document) -> Document:
    doc.discrepancies, doc.validation_errors = None, None
    try:
        text, parse_method = extract_text(doc.file_path)
    except ParseError as e:
        doc.status = DocStatus.SCHEMA_FAILED.value
        doc.validation_errors = [f"parse: {e}"]
        db.commit()
        return doc

    doc.raw_text = text
    res = extract_document(text)
    doc.extraction_method = f"{res.method}+{parse_method}"
    doc.extraction_trail = res.trail
    doc.extracted_data = res.data.model_dump() if res.data else res.raw
    if res.data:
        doc.doc_type, doc.po_number = res.data.doc_type, res.data.po_number

    if res.errors or not res.data:
        doc.status = DocStatus.SCHEMA_FAILED.value      # structured routing to human review
        doc.validation_errors = res.errors
    else:
        rec = reconcile(db, res.data)
        doc.status, doc.discrepancies = rec.status, rec.discrepancies
    db.commit()
    db.refresh(doc)
    return doc
