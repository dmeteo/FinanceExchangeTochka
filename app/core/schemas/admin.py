from pydantic import BaseModel, Field
from uuid import UUID

class DepositRequest(BaseModel):
    user_id: UUID
    ticker: str = Field(..., pattern=r'^[A-Z]{2,10}$')
    amount: int = Field(..., gt=0)

class WithdrawRequest(BaseModel):
    user_id: UUID = Field(..., example="35b0884d-9a1d-47b0-91c7-eecf0ca56bc8")
    ticker: str = Field(..., pattern=r'^[A-Z]{2,10}$', example="MEMCOIN")
    amount: int = Field(..., gt=0, example=500)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "35b0884d-9a1d-47b0-91c7-eecf0ca56bc8",
                "ticker": "MEMCOIN",
                "amount": 500
            }
        }