from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models.transaction import Transaction
from app.repositories.base import BaseRepository

class TransactionRepository(BaseRepository):
    def __init__(self):
        super().__init__(Transaction)

    async def get_by_ticker(self, db: AsyncSession, ticker: str, limit: int = 10) -> list[Transaction]:
        result = await db.execute(
            select(Transaction)
            .where(Transaction.ticker == ticker)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
