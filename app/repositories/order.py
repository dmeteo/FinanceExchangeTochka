import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.exceptions import InsufficientBalanceException
from repositories import balance_repo
from core.models.order import Order
from core.schemas.order import LimitOrderBody, OrderStatus
from .base import BaseRepository

class OrderRepository(BaseRepository[Order, LimitOrderBody, LimitOrderBody]):
    def __init__(self):
        super().__init__(Order)

    async def get_by_user(self, db: AsyncSession, user_id) -> list[Order]:
        result = await db.execute(
            select(Order).where(Order.user_id == user_id)
        )
        return result.scalars().all()

    async def get_user_orders(self, db: AsyncSession, user_id: UUID):
        result = await db.execute(
            select(Order).where(
                Order.user_id == user_id,
                Order.status.in_(["NEW", "PARTIALLY_EXECUTED"])
            )
        )
        return result.scalars().all()
    
    async def get(self, db: AsyncSession, order_id: UUID) -> Order | None:
        return await db.get(Order, order_id)

    async def cancel(self, db: AsyncSession, order: Order):
        if order.status in [OrderStatus.EXECUTED, OrderStatus.CANCELLED]:
            return order
        remaining_qty = order.qty - order.filled
        if remaining_qty > 0:
            if order.direction == "BUY" and order.price:
                try:
                    await balance_repo.unfreeze(
                        db, order.user_id, "RUB", remaining_qty * order.price
                    )
                except InsufficientBalanceException:
                    logging.warning(f"Нет замороженного RUB для возврата при отмене BUY ордера {order.id}")
            elif order.direction == "SELL":
                try:
                    await balance_repo.unfreeze(
                        db, order.user_id, order.ticker, remaining_qty
                    )
                except InsufficientBalanceException:
                    logging.warning(f"Нет замороженного {order.ticker} для возврата при отмене SELL ордера {order.id}")
        order.status = OrderStatus.CANCELLED
        await db.commit()
        await db.refresh(order)
        return order

    
    async def get_bids(self, db: AsyncSession, ticker: str, limit: int):
        result = await db.execute(
            select(Order)
            .where(
                Order.ticker == ticker,
                Order.direction == "BUY",
                Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])
            )
            .order_by(Order.price.desc(), Order.created_at.asc())  
            .limit(limit)
        )
        return result.scalars().all()

    async def get_asks(self, db: AsyncSession, ticker: str, limit: int):
        result = await db.execute(
            select(Order)
            .where(
                Order.ticker == ticker,
                Order.direction == "SELL",
                Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])
            )
            .order_by(Order.price.asc(), Order.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()
