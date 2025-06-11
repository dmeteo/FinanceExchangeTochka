from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import uuid

class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buy_order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id'))
    sell_order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id'))
    ticker = Column(String(10), nullable=False)
    amount = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)

    buy_order = relationship("Order", foreign_keys=[buy_order_id], back_populates="buy_transactions")
    sell_order = relationship("Order", foreign_keys=[sell_order_id], back_populates="sell_transactions")

    def __repr__(self):
        return f"<Transaction(ticker={self.ticker}, amount={self.amount}, price={self.price})>"