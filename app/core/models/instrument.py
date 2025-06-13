from sqlalchemy import Column, String
from .base import Base, TimestampMixin

class Instrument(Base, TimestampMixin):
    __tablename__ = "instruments"
    
    ticker = Column(String(10), primary_key=True)
    name = Column(String(128), nullable=False)

    def __repr__(self):
        return f"<Instrument(ticker={self.ticker}, name={self.name})>"