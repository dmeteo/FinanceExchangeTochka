import logging
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.exceptions import InsufficientBalanceException
from core.models.balance import Balance

class BalanceRepository:
    async def get_user_balances(
        self, 
        db: AsyncSession, 
        user_id: UUID
    ) -> list[Balance]:
        result = await db.execute(
            select(Balance).where(Balance.user_id == user_id)
        )
        return result.scalars().all()

    async def get_balances_by_ticker(self, db: AsyncSession, ticker: str) -> list[Balance]:
        result = await db.execute(
            select(Balance).where(Balance.ticker == ticker)
        )
        return result.scalars().all()

    async def get_balance(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        ticker: str, 
        for_update: bool = False
    ) -> Balance | None:
        stmt = select(Balance).where(Balance.user_id == user_id, Balance.ticker == ticker)
        if for_update:
            stmt = stmt.with_for_update()
        result = await db.execute(stmt)
        return result.scalars().first()

    async def deposit(self, db: AsyncSession, user_id: UUID, ticker: str, amount: int):
        logging.info(f"Deposit: user={user_id}, ticker={ticker}, amount={amount}")
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        balance = await self.get_balance(db, user_id, ticker, for_update=True)
        if balance:
            balance.amount += amount
        else:
            balance = Balance(user_id=user_id, ticker=ticker, amount=amount, frozen=0)
            db.add(balance)

    async def withdraw(self, db: AsyncSession, user_id: UUID, ticker: str, amount: int):
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        balance = await self.get_balance(db, user_id, ticker, for_update=True)
        if not balance:
            raise HTTPException(status_code=404, detail="Balance entry not found")
        if balance.amount < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        balance.amount -= amount
        db.add(balance)

    async def transfer(
        self,
        db: AsyncSession,
        from_user_id: UUID,
        to_user_id: UUID,
        ticker: str,
        qty: int,
    ):
        if qty <= 0:
            raise HTTPException(status_code=400, detail="Transfer qty must be positive")
        from_balance = await self.get_balance(db, from_user_id, ticker, for_update=True)
        to_balance = await self.get_balance(db, to_user_id, ticker, for_update=True)
        if not from_balance or from_balance.amount < qty:
            raise InsufficientBalanceException("Not enough funds for transfer")
        from_balance.amount -= qty
        db.add(from_balance)
        if not to_balance:
            to_balance = Balance(user_id=to_user_id, ticker=ticker, amount=0, frozen=0)
            db.add(to_balance)
        to_balance.amount += qty
        db.add(to_balance)

    async def freeze(self, db: AsyncSession, user_id: UUID, ticker: str, amount: int):
        logging.info(f"Freeze: user={user_id}, ticker={ticker}, amount={amount}")
        if amount <= 0:
            raise InsufficientBalanceException("Freeze amount must be positive")
        balance = await self.get_balance(db, user_id, ticker, for_update=True)
        if not balance or balance.amount < amount:
            raise InsufficientBalanceException("Недостаточно средств для резервации")
        balance.amount -= amount
        balance.frozen += amount
        db.add(balance)

    async def unfreeze(self, db: AsyncSession, user_id: UUID, ticker: str, amount: int):
        logging.info(f"Unfreeze: user={user_id}, ticker={ticker}, amount={amount}")
        if amount <= 0:
            raise InsufficientBalanceException("Unfreeze amount must be positive")
        balance = await self.get_balance(db, user_id, ticker, for_update=True)
        if not balance or balance.frozen < amount:
            raise InsufficientBalanceException("Недостаточно замороженного баланса")
        balance.amount += amount
        balance.frozen -= amount
        db.add(balance)

    async def spend_frozen(self, db: AsyncSession, user_id: UUID, ticker: str, amount: int):
        logging.info(f"Spend frozen: user={user_id}, ticker={ticker}, amount={amount}")
        if amount <= 0:
            raise InsufficientBalanceException("Spend amount must be positive")
        balance = await self.get_balance(db, user_id, ticker, for_update=True)
        if not balance or balance.frozen < amount:
            raise InsufficientBalanceException("Недостаточно замороженного баланса для списания")
        balance.frozen -= amount
        db.add(balance)
