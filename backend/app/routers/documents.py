import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import DocStatus, Document, PurchaseOrder
from ..schemas import DocumentDetail, DocumentOut, ReviewAction
from ..services.workflow import process_document

router = APIRouter(tags=["documents"])
REVIEWABLE = {DocStatus.FLAGGED.value, DocStatus.SCHEMA_FAILED.value}


def _po_dict(po: PurchaseOrder) -> dict:
    return {
        "po_number": po.po_number, "vendor": po.vendor, "carrier": po.carrier,
        "total_amount": float(po.total_amount),
        "total_weight": float(po.total_weight) if po.total_weight is not None else None,
        "delivery_date": po.delivery_date.isoformat() if po.delivery_date else None,
        "line_items": [{"description": li.description, "quantity": float(li.quantity),
                        "unit_price": float(li.unit_price), "amount": float(li.amount)}
                       for li in po.line_items],
    }


def _detail(db: Session, doc: Document) -> DocumentDetail:
    d = DocumentDetail.model_validate(doc)
    d.raw_text = doc.raw_text
    if doc.po_number:
        po = db.query(PurchaseOrder).filter_by(po_number=doc.po_number).first()
        d.expected_po = _po_dict(po) if po else None
    return d


def _get(db: Session, doc_id: int) -> Document:
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("/documents/upload", response_model=DocumentDetail, status_code=201)
def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = file.file.read()
    if not (file.filename or "").lower().endswith(".pdf") or not content.startswith(b"%PDF"):
        raise HTTPException(400, "Only PDF files are accepted")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB")
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    path = Path(settings.upload_dir) / f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    path.write_bytes(content)
    doc = Document(filename=file.filename, file_path=str(path))
    db.add(doc)
    db.commit()
    return _detail(db, process_document(db, doc))


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(status: str | None = Query(None), db: Session = Depends(get_db)):
    q = db.query(Document).order_by(Document.created_at.desc())
    if status:
        q = q.filter(Document.status == status.upper())
    return q.all()


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    return _detail(db, _get(db, doc_id))


@router.get("/documents/{doc_id}/file")
def get_file(doc_id: int, db: Session = Depends(get_db)):
    doc = _get(db, doc_id)
    return FileResponse(doc.file_path, media_type="application/pdf", filename=doc.filename,
                        content_disposition_type="inline")


def _review(db: Session, doc_id: int, status: DocStatus, body: ReviewAction):
    doc = _get(db, doc_id)
    if doc.status not in REVIEWABLE:
        raise HTTPException(409, f"Document in status {doc.status} is not awaiting review")
    doc.status, doc.reviewer_note = status.value, body.note
    db.commit()
    return _detail(db, doc)


@router.post("/documents/{doc_id}/approve", response_model=DocumentDetail)
def approve(doc_id: int, body: ReviewAction = ReviewAction(), db: Session = Depends(get_db)):
    return _review(db, doc_id, DocStatus.APPROVED, body)


@router.post("/documents/{doc_id}/reject", response_model=DocumentDetail)
def reject(doc_id: int, body: ReviewAction = ReviewAction(), db: Session = Depends(get_db)):
    return _review(db, doc_id, DocStatus.REJECTED, body)


@router.post("/documents/{doc_id}/reprocess", response_model=DocumentDetail)
def reprocess(doc_id: int, db: Session = Depends(get_db)):
    return _detail(db, process_document(db, _get(db, doc_id)))


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    rows = db.query(Document.status, func.count()).group_by(Document.status).all()
    return {s: n for s, n in rows}


@router.get("/purchase-orders")
def purchase_orders(db: Session = Depends(get_db)):
    return [_po_dict(p) for p in db.query(PurchaseOrder).order_by(PurchaseOrder.po_number)]
