from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models.balance import Balance

class BalanceRepository:
    async def get_user_balances(
        self, 
        db: AsyncSession, 
        user_id: UUID
    ) -> list[Balance]:
        result = await db.execute(
            select(Balance)
            .where(Balance.user_id == user_id)
        )
        return result.scalars().all()
    
    async def deposit(
        self, db: AsyncSession, user_id: UUID, ticker: str, amount: int
    ):
        result = await db.execute(
            select(Balance).where(
                Balance.user_id == user_id,
                Balance.ticker == ticker,
            )
        )
        balance = result.scalars().first()

        if balance:
            balance.amount += amount
        else:
            balance = Balance(user_id=user_id, ticker=ticker, amount=amount)
            db.add(balance)

        await db.commit()
        await db.refresh(balance)

    async def withdraw(
    self, db: AsyncSession, user_id: UUID, ticker: str, amount: int
    ):
        result = await db.execute(
            select(Balance).where(
                Balance.user_id == user_id,
                Balance.ticker == ticker,
            )
        )
        balance = result.scalars().first()
        if not balance:
            raise HTTPException(status_code=404, detail="Balance entry not found")

        if balance.amount < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")

        balance.amount -= amount
        await db.commit()
        await db.refresh(balance)

    async def get_balance(self, db: AsyncSession, user_id: UUID, ticker: str) -> Balance | None:
        result = await db.execute(
            select(Balance).where(Balance.user_id == user_id, Balance.ticker == ticker)
        )
        return result.scalars().first()
    
    async def transfer(
        self,
        db: AsyncSession,
        from_user_id: UUID,
        to_user_id: UUID,
        ticker: str,
        qty: int,
        price: int
    ):
        from_balance = await self.get_balance(db, from_user_id, ticker)
        to_balance = await self.get_balance(db, to_user_id, ticker)

        if not from_balance or from_balance.amount < qty:
            raise HTTPException(status_code=400, detail="Insufficient balance for transfer")

        from_balance.amount -= qty

        if not to_balance:
            to_balance = Balance(user_id=to_user_id, ticker=ticker, amount=0)
            db.add(to_balance)

        to_balance.amount += qty

        db.add(from_balance)
        db.add(to_balance)

    