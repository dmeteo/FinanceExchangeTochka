from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

from sqlalchemy import Enum as SqlEnum
from core.types import Direction, OrderStatus
import uuid

class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
    ticker = Column(String(10), nullable=False)
    direction = Column(SqlEnum(Direction, name='order_directions', native_enum=False), nullable=False)
    qty = Column(Integer, nullable=False)
    price = Column(Integer)
    status = Column(SqlEnum(OrderStatus, name="order_statuses", native_enum=False), default=OrderStatus.NEW)
    filled = Column(Integer, default=0)

    user = relationship("User", back_populates="orders", passive_deletes=True)
    buy_transactions = relationship("Transaction", foreign_keys="[Transaction.buy_order_id]", back_populates="buy_order", cascade="all, delete-orphan",
        passive_deletes=True)
    sell_transactions = relationship("Transaction", foreign_keys="[Transaction.sell_order_id]", back_populates="sell_order", cascade="all, delete-orphan",
        passive_deletes=True)

    def __repr__(self):
        return f"<Order(id={self.id}, ticker={self.ticker}, qty={self.qty}, price={self.price})>"