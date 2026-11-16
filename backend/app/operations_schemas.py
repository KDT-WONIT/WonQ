from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Quantity = Annotated[int, Field(ge=0, le=1_000_000)]


class LineCreate(BaseModel):
    item_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    name: ShortText
    tracking: Literal["individual", "quantity"]
    quantity: Annotated[int, Field(gt=0, le=1_000_000)]
    location: ShortText

    @model_validator(mode="after")
    def label_limit(self):
        if self.tracking == "individual" and self.quantity > 100:
            raise ValueError("개별 자산은 품목 행당 최대 100개까지 접수할 수 있습니다.")
        return self


class IntakeCreate(BaseModel):
    document_number: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    department: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    lines: Annotated[list[LineCreate], Field(min_length=1, max_length=25)]


class IntakeReview(BaseModel):
    decision: Literal["approve", "reject"]
    quantities: dict[UUID, Quantity] = Field(default_factory=dict)
    note: Note | None = None


class ReceiptLine(BaseModel):
    line_id: UUID
    received: Quantity
    accepted: Quantity
    serials: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]] = Field(default_factory=list, max_length=100)
    note: Note | None = None


class InspectionReceipt(BaseModel):
    lines: Annotated[list[ReceiptLine], Field(min_length=1, max_length=25)]


class SignReceipt(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class LineView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    item_code: str
    name: str
    tracking: str
    location: str
    submitted_quantity: int
    approved_quantity: int | None
    received_quantity: int | None
    accepted_quantity: int | None
    labels: list[UUID]
    variance_note: str | None


class IntakeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    vendor_id: str
    document_number: str
    department: str
    status: str
    review_note: str | None
    signer_name: str | None
    signed_at: datetime | None
    received_at: datetime | None
    lines: list[LineView]


class StockUse(BaseModel):
    operation_id: UUID
    quantity: Annotated[int, Field(gt=0, le=1_000_000)]
    purpose: Literal["issue", "consume"]
    note: Note


class StockThreshold(BaseModel):
    quantity: Quantity


class AuditCreate(BaseModel):
    title: ShortText
    assigned_to: ShortText | None = None
    location: ShortText | None = None
    scheduled_for: AwareDatetime | None = None


class AuditObservation(BaseModel):
    qr_token: UUID | None = None
    target_id: UUID | None = None
    quantity: Quantity
    location: ShortText | None = None

    @model_validator(mode="after")
    def validate_target(self):
        if (self.qr_token is None) == (self.target_id is None):
            raise ValueError("QR 또는 실사 대상 ID를 하나만 입력하세요.")
        if self.quantity > 0 and self.location is None:
            raise ValueError("수량이 1 이상이면 확인 위치를 입력하세요.")
        if self.quantity == 0 and self.location is not None:
            raise ValueError("미발견 시 확인 위치를 비워 주세요.")
        return self
