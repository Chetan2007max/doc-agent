"""Reconcile extracted data against the PO in the database with tolerance-based flagging."""
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..models import DocStatus, PurchaseOrder
from ..schemas import ExtractedDocument


@dataclass
class ReconResult:
    status: str
    discrepancies: list[dict]


def _pct(actual: float, expected: float) -> float:
    if expected == 0:
        return 0.0 if actual == 0 else 100.0
    return (actual - expected) / expected * 100


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _d(field, extracted, expected, message, severity="high", diff_pct: Optional[float] = None):
    return {"field": field, "extracted": extracted, "expected": expected,
            "message": message, "severity": severity,
            "diff_pct": None if diff_pct is None else round(diff_pct, 2)}


def reconcile(db: Session, doc: ExtractedDocument) -> ReconResult:
    tol = settings.tolerance_pct
    po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == doc.po_number).first()
    if not po:
        return ReconResult(DocStatus.FLAGGED.value, [
            _d("po_number", doc.po_number, None, f"PO {doc.po_number} not found in database")])

    out: list[dict] = []

    if doc.total_cost is not None:
        exp = float(po.total_amount)
        p = _pct(doc.total_cost, exp)
        if abs(p) > tol:
            out.append(_d("total_cost", doc.total_cost, exp,
                          f"Invoice shows ${doc.total_cost:,.2f}, PO shows ${exp:,.2f} ({p:+.2f}%, tolerance {tol}%)",
                          diff_pct=p))

    if doc.total_weight is not None and po.total_weight is not None:
        exp = float(po.total_weight)
        p = _pct(doc.total_weight, exp)
        if abs(p) > tol:
            out.append(_d("total_weight", doc.total_weight, exp,
                          f"Weight {doc.total_weight:,.2f} kg vs PO {exp:,.2f} kg ({p:+.2f}%)",
                          "medium", p))

    if doc.carrier_name and po.carrier:
        a, b = _key(doc.carrier_name), _key(po.carrier)
        if a not in b and b not in a:
            out.append(_d("carrier_name", doc.carrier_name, po.carrier,
                          f"Carrier {doc.carrier_name!r} does not match PO carrier {po.carrier!r}", "medium"))

    if doc.doc_type == "INVOICE":   # BoL line items are cargo, not billable charges
        po_items = {_key(li.description): li for li in po.line_items}
        seen = set()
        for li in doc.line_items:
            k = _key(li.description)
            ref = po_items.get(k)
            if not ref:
                out.append(_d(f"line_item:{li.description}", li.amount, None,
                              f"Line '{li.description}' is not on the PO", "high"))
                continue
            seen.add(k)
            if abs(li.quantity - float(ref.quantity)) > 1e-6:
                out.append(_d(f"line_item:{li.description}.quantity", li.quantity, float(ref.quantity),
                              f"'{li.description}' qty {li.quantity:g} vs PO {float(ref.quantity):g}", "medium"))
            p = _pct(li.unit_price, float(ref.unit_price))
            if abs(p) > tol:
                out.append(_d(f"line_item:{li.description}.unit_price", li.unit_price, float(ref.unit_price),
                              f"'{li.description}' unit price ${li.unit_price:,.2f} vs PO ${float(ref.unit_price):,.2f} ({p:+.2f}%)",
                              "medium", p))
        for k, ref in po_items.items():
            if k not in seen and doc.line_items:
                out.append(_d(f"line_item:{ref.description}", None, float(ref.amount),
                              f"PO line '{ref.description}' missing from invoice", "low"))

    return ReconResult(DocStatus.FLAGGED.value if out else DocStatus.AUTO_APPROVED.value, out)
