from uuid import UUID
from pydantic import BaseModel, Field

class BalanceOperation(BaseModel):
    user_id: UUID
    ticker: str = Field(..., example="MEMCOIN")
    amount: int = Field(..., gt=0, le=1_000_000_000)