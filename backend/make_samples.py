"""python make_samples.py -> generates test PDFs in ./samples (uses PyMuPDF only)"""
from pathlib import Path

import pymupdf as fitz

from app.seed import PO_DATA

OUT = Path("samples")
OUT.mkdir(exist_ok=True)
PO = {p[0]: p for p in PO_DATA}


def write_pdf(name, lines):
    doc = fitz.open()
    page = doc.new_page()
    y = 60
    for ln in lines:
        page.insert_text((50, y), ln, fontname="cour", fontsize=10)
        y += 16
    doc.save(OUT / name)


def invoice(po_num, inv_no, items=None, total_override=None, with_total=True, po_label=None):
    _, carrier, weight, delivery, po_items = PO[po_num]
    items = items or po_items
    sub = round(sum(q * p for _, q, p in items), 2)
    lines = ["FREIGHT INVOICE", "", f"Invoice Number: {inv_no}", f"PO Number: {po_label or po_num}",
             f"Carrier: {carrier}", f"Delivery Date: {delivery}", f"Total Weight: {weight:,} kg", "",
             "Description                      Qty   Unit Price   Amount"]
    lines += [f"{d}   {q:g}   {p:.2f}   {q * p:.2f}" for d, q, p in items]
    lines.append("")
    if with_total:
        lines += [f"Subtotal: {sub:.2f}", "Tax: 0.00", f"Total Due: ${(total_override or sub):,.2f}"]
    else:
        lines += ["Payment terms: Net 30"]
    return lines


def bol(po_num, bol_no, weight=None):
    _, carrier, w, delivery, _ = PO[po_num]
    return ["BILL OF LADING", "", f"BOL Number: {bol_no}", f"PO Number: {po_num}", f"Carrier: {carrier}",
            f"Delivery Date: {delivery}", f"Total Weight: {(weight or w):,} kg", "",
            "Shipper: Acme Exports Pvt Ltd", "Consignee: Global Retail Inc", "Packages: 24 pallets"]


write_pdf("1_invoice_match_PO-1001.pdf", invoice("PO-1001", "INV-2026-0042"))
d, q, p = PO["PO-1002"][4][0]
write_pdf("2_invoice_overcharge_PO-1002.pdf",
          invoice("PO-1002", "INV-2026-0043", items=[(d, q, 380.00)] + PO["PO-1002"][4][1:]))
write_pdf("3_invoice_unknown_po.pdf", invoice("PO-1001", "INV-2026-0044", po_label="PO-9999"))
write_pdf("4_bol_match_PO-1004.pdf", bol("PO-1004", "BOL-7781"))
write_pdf("5_bol_weight_mismatch_PO-1003.pdf", bol("PO-1003", "BOL-7782", weight=5600))
write_pdf("6_invoice_missing_total_PO-1005.pdf", invoice("PO-1005", "INV-2026-0045", with_total=False))
write_pdf("7_invoice_wrong_total_PO-1006.pdf", invoice("PO-1006", "INV-2026-0046", total_override=9999.00))

# image-only (scanned) PDF -> exercises OCR fallback path
src = fitz.open(OUT / "1_invoice_match_PO-1001.pdf")
pix = src[0].get_pixmap(dpi=150)
scan = fitz.open()
pg = scan.new_page()
pg.insert_image(pg.rect, pixmap=pix)
scan.save(OUT / "8_scanned_invoice_PO-1001.pdf")
print("Generated", len(list(OUT.glob('*.pdf'))), "sample PDFs in ./samples")
