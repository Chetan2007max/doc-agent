import enum
from datetime import datetime

from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from .db import Base


class DocStatus(str, enum.Enum):
    PENDING = "PENDING"
    AUTO_APPROVED = "AUTO_APPROVED"    # reconciled within tolerance, no human needed
    FLAGGED = "FLAGGED"                # discrepancy vs PO -> human review
    SCHEMA_FAILED = "SCHEMA_FAILED"    # extraction failed schema assertion -> human review
    APPROVED = "APPROVED"              # operator override / approval
    REJECTED = "REJECTED"


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True)
    po_number = Column(String(32), unique=True, nullable=False, index=True)
    vendor = Column(String(120), nullable=False)
    carrier = Column(String(120))
    total_amount = Column(Numeric(12, 2), nullable=False)
    total_weight = Column(Numeric(12, 2))          # kg
    delivery_date = Column(Date)
    line_items = relationship("POLineItem", cascade="all, delete-orphan", back_populates="po")


class POLineItem(Base):
    __tablename__ = "po_line_items"
    id = Column(Integer, primary_key=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    description = Column(String(200), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    po = relationship("PurchaseOrder", back_populates="line_items")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    doc_type = Column(String(16))
    status = Column(String(20), default=DocStatus.PENDING.value, index=True, nullable=False)
    po_number = Column(String(32), index=True)
    extraction_method = Column(String(32))
    raw_text = Column(Text)
    extracted_data = Column(JSON)
    discrepancies = Column(JSON)
    validation_errors = Column(JSON)
    extraction_trail = Column(JSON)
    reviewer_note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
