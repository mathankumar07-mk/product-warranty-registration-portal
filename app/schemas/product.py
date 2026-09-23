from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductCreate(BaseModel):
    product_name: str = Field(..., min_length=2, max_length=120)
    brand: str = Field(..., min_length=2, max_length=80)
    model_number: str | None = Field(default=None, max_length=80)
    serial_number: str | None = Field(default=None, max_length=120)
    purchase_date: date
    invoice_number: str = Field(..., min_length=2, max_length=80)
    warranty_period_months: int = Field(default=12, ge=1, le=120)
    warranty_expiry_date: date | None = None

    @model_validator(mode="after")
    def validate_expiry_date(self):
        if self.warranty_expiry_date and self.warranty_expiry_date < self.purchase_date:
            raise ValueError("warranty_expiry_date must be on or after purchase_date")
        return self


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    product_name: str
    brand: str
    model_number: str | None
    serial_number: str | None
    purchase_date: date
    invoice_number: str
    warranty_period_months: int
    warranty_expiry_date: date
    status: str
    created_at: datetime
