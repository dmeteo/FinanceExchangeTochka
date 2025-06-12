from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base

class Balance(Base):
    __tablename__ = "balances"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    ticker = Column(String(10), primary_key=True)
    amount = Column(Integer, default=0)
    frozen = Column(Integer, default=0)

    user = relationship("User", back_populates="balances")

    def __repr__(self):
        return f"<Balance(user_id={self.user_id}, ticker={self.ticker}, amount={self.amount})>"