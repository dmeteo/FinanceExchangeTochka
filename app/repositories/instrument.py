from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.instrument import Instrument
from core.schemas.instrument import InstrumentCreate
from .base import BaseRepository

class InstrumentRepository(BaseRepository[Instrument, InstrumentCreate, InstrumentCreate]):
    def __init__(self):
        super().__init__(Instrument)

    async def get_by_ticker(self, db: AsyncSession, ticker: str) -> Instrument | None:
        result = await db.execute(select(Instrument).where(Instrument.ticker == ticker))
        return result.scalar_one_or_none()
    
    async def delete_by_ticker(self, db: AsyncSession, ticker: str):
        result = await db.execute(select(Instrument).where(Instrument.ticker == ticker))
        instrument = result.scalar_one_or_none()
        if not instrument:
            raise HTTPException(status_code=404, detail="Instrument not found")

        await db.delete(instrument)
        await db.commit()

    async def get_all(self, db: AsyncSession) -> list[Instrument]:
        result = await db.execute(select(Instrument))
        return result.scalars().all()
