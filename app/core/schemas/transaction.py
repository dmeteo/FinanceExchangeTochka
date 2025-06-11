from pydantic import BaseModel, Field
from datetime import datetime

class Transaction(BaseModel):
    ticker: str = Field(..., example="MEMCOIN")
    amount: int = Field(..., example=100)
    price: int = Field(..., example=150)
    created_at: datetime = Field(..., alias="timestamp")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }