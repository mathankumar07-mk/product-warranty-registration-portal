from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WarrantyClaimCreate(BaseModel):
    product_id: int
    claim_type: str = Field(..., min_length=2, max_length=50)
    description: str = Field(..., min_length=10, max_length=2000)


class WarrantyClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    user_id: int
    claim_type: str
    description: str
    status: str
    created_at: datetime
