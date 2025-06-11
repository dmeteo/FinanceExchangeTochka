from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models.order import Order, OrderStatus
from core.models.transaction import Transaction
from repositories.order import OrderRepository
from repositories.balance import BalanceRepository

class OrderMatchingService:
    def __init__(self, order_repo: OrderRepository, balance_repo: BalanceRepository):
        self.order_repo = order_repo
        self.balance_repo = balance_repo

    async def match_order(self, db: AsyncSession, order: Order):
        is_buy = order.direction == "BUY"

        base_query = select(Order).where(
            Order.ticker == order.ticker,
            Order.status == OrderStatus.NEW,
            Order.direction != order.direction,
        )

        # Добавляем проверку на цену — только если она есть
        if order.price is not None:
            price_condition = (
                Order.price <= order.price if is_buy else Order.price >= order.price
            )
            base_query = base_query.where(price_condition)

        base_query = base_query.order_by(
            Order.price.asc() if is_buy else Order.price.desc()
        )

        result = await db.execute(base_query)
        candidates = result.scalars().all()

        remaining_qty = order.qty

        for match in candidates:
            available_qty = match.qty - match.filled
            trade_qty = min(available_qty, remaining_qty)
            trade_price = match.price if match.price is not None else order.price

            if trade_qty <= 0 or trade_price is None:
                continue

            transaction = Transaction(
                buy_order_id=order.id if is_buy else match.id,
                sell_order_id=match.id if is_buy else order.id,
                ticker=order.ticker,
                amount=trade_qty,
                price=trade_price
            )

            await self.balance_repo.transfer(
                db,
                from_user_id=match.user_id if is_buy else order.user_id,
                to_user_id=order.user_id if is_buy else match.user_id,
                ticker=order.ticker,
                qty=trade_qty,
                price=trade_price
            )

            order.filled += trade_qty
            match.filled += trade_qty

            if match.filled == match.qty:
                match.status = OrderStatus.EXECUTED

            db.add(transaction)
            db.add(match)

            remaining_qty -= trade_qty
            if remaining_qty <= 0:
                break

        if order.filled == 0:
            order.status = OrderStatus.CANCELLED
        elif order.filled < order.qty:
            order.status = OrderStatus.PARTIALLY_EXECUTED
        else:
            order.status = OrderStatus.EXECUTED

        db.add(order)
        await db.commit()

