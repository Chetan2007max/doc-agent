"""python -m app.seed [--reset]  -> 8 mock purchase orders"""
import sys
from datetime import date

from .db import Base, SessionLocal, engine
from .models import POLineItem, PurchaseOrder

PO_DATA = [
    ("PO-1001", "Maersk Line", 18500, "2026-10-20", [("Ocean Freight 40ft Container", 2, 2000.00), ("Customs Clearance", 1, 600.00), ("Port Handling", 1, 400.00)]),
    ("PO-1002", "DHL Freight", 2400, "2026-10-12", [("Air Freight Pallet", 10, 350.00), ("Fuel Surcharge", 1, 250.00)]),
    ("PO-1003", "FedEx Freight", 5200, "2026-10-25", [("LTL Freight Shipment", 4, 780.00), ("Liftgate Service", 1, 120.00)]),
    ("PO-1004", "Blue Dart", 900, "2026-10-15", [("Surface Freight Cartons", 50, 45.00), ("Last Mile Delivery", 1, 300.00)]),
    ("PO-1005", "MSC", 27000, "2026-11-02", [("Ocean Freight 20ft Container", 3, 1500.00), ("Documentation Fee", 1, 150.00), ("Terminal Handling", 3, 220.00)]),
    ("PO-1006", "UPS Freight", 6400, "2026-10-30", [("Ground Freight Pallet", 8, 410.00), ("Inside Delivery", 1, 95.00)]),
    ("PO-1007", "Maersk Line", 11000, "2026-11-10", [("Reefer Container 40ft", 1, 4200.00), ("Cold Chain Monitoring", 1, 350.00)]),
    ("PO-1008", "Delhivery", 3600, "2026-10-18", [("Express Parcel Freight", 120, 18.50), ("Packaging Surcharge", 1, 200.00)]),
]


def seed(reset: bool = False):
    Base.metadata.create_all(engine)
    db = SessionLocal()
    if reset:
        db.query(POLineItem).delete()
        db.query(PurchaseOrder).delete()
        db.commit()
    if db.query(PurchaseOrder).count():
        print("POs already present (use --reset to reseed)")
        return
    for num, carrier, weight, delivery, items in PO_DATA:
        total = round(sum(q * p for _, q, p in items), 2)
        po = PurchaseOrder(po_number=num, vendor=carrier, carrier=carrier, total_amount=total,
                           total_weight=weight, delivery_date=date.fromisoformat(delivery))
        po.line_items = [POLineItem(description=d, quantity=q, unit_price=p, amount=round(q * p, 2)) for d, q, p in items]
        db.add(po)
    db.commit()
    print(f"Seeded {len(PO_DATA)} purchase orders")


if __name__ == "__main__":
    seed("--reset" in sys.argv)
