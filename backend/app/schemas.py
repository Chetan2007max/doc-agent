"""Single source of truth: ExtractedDocument generates the JSON schema sent to the LLM
AND strictly validates what comes back."""
import re
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LineItem(BaseModel):
    description: str = Field(min_length=1)
    quantity: float = Field(ge=0)
    unit_price: float = Field(ge=0)
    amount: float = Field(ge=0)


class ExtractedDocument(BaseModel):
    doc_type: Literal["INVOICE", "BOL"]
    po_number: str = Field(min_length=3)
    invoice_number: Optional[str] = None
    carrier_name: Optional[str] = None
    currency: str = "USD"
    line_items: list[LineItem] = []
    subtotal: Optional[float] = Field(default=None, ge=0)
    tax: Optional[float] = Field(default=None, ge=0)
    total_cost: Optional[float] = Field(default=None, ge=0)
    total_weight: Optional[float] = Field(default=None, ge=0, description="kilograms")
    delivery_date: Optional[str] = Field(default=None, description="ISO date YYYY-MM-DD")

    @field_validator("po_number")
    @classmethod
    def _po(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9\-]{2,}", v):
            raise ValueError(f"malformed PO number: {v!r}")
        return v

    @field_validator("delivery_date")
    @classmethod
    def _date(cls, v):
        if v is None:
            return v
        try:
            return date.fromisoformat(v).isoformat()
        except ValueError:
            raise ValueError(f"delivery_date must be ISO YYYY-MM-DD, got {v!r}")

    @model_validator(mode="after")
    def _invoice_needs_total(self):
        if self.doc_type == "INVOICE" and self.total_cost is None:
            raise ValueError("total_cost is required for invoices")
        return self


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    doc_type: Optional[str] = None
    status: str
    po_number: Optional[str] = None
    extraction_method: Optional[str] = None
    extracted_data: Optional[dict[str, Any]] = None
    discrepancies: Optional[list[dict[str, Any]]] = None
    validation_errors: Optional[list[str]] = None
    extraction_trail: Optional[list[dict[str, Any]]] = None
    reviewer_note: Optional[str] = None
    created_at: Optional[datetime] = None


class DocumentDetail(DocumentOut):
    raw_text: Optional[str] = None
    expected_po: Optional[dict[str, Any]] = None


class ReviewAction(BaseModel):
    note: Optional[str] = None
