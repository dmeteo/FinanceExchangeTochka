from uuid import UUID
from pydantic import BaseModel, UUID4, Field
from typing import List, Optional, Union
from enum import Enum
from datetime import datetime

class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"

class OrderBookLevel(BaseModel):
    price: float
    qty: int

class L2OrderBook(BaseModel):
    bid_levels: List[OrderBookLevel]
    ask_levels: List[OrderBookLevel]

class CreateOrderResponse(BaseModel):
    success: bool = True
    order_id: UUID

class LimitOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int = Field(..., gt=0, le=1_000_000_000)
    price: int = Field(..., gt=0, le=1_000_000_000)

class MarketOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int = Field(..., gt=0, le=1_000_000_000)

class Order(BaseModel):
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    created_at: datetime = Field(..., alias="timestamp")
    filled: int = 0

    class Config:
        from_attributes = True
        
class LimitOrder(Order):
    body: LimitOrderBody

class MarketOrder(Order):
    body: MarketOrderBody

OrderResponse = Union[LimitOrder, MarketOrder]