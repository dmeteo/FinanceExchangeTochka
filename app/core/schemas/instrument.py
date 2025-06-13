from pydantic import BaseModel, Field


class InstrumentBase(BaseModel):
    name: constr(max_length=50) = Field(..., min_length=1, example="Meme Coin")
    ticker: str = Field(..., pattern=r'^[A-Z]{2,10}$', example="MEMCOIN")

class InstrumentCreate(InstrumentBase):
    pass

class Instrument(InstrumentBase):
    class Config:
        from_attributes = True

class InstrumentResponse(BaseModel):
    success: bool = True


__all__ = [
    'InstrumentBase',
    'InstrumentCreate',
    'Instrument',
    'InstrumentResponse'
]