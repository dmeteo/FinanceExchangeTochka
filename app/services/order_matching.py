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
        if order.status == OrderStatus.EXECUTED:
            return

        is_buy = order.direction == "BUY"

        base_query = select(Order).where(
            Order.ticker == order.ticker,
            Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
            Order.direction != order.direction,
        )

        if order.price is not None:
            price_condition = Order.price <= order.price if is_buy else Order.price >= order.price
            base_query = base_query.where(price_condition)

        base_query = base_query.with_for_update().order_by(
            Order.price.asc() if is_buy else Order.price.desc(),
            Order.created_at.asc()
        )

        result = await db.execute(base_query)
        candidates = result.scalars().all()
        remaining_qty = order.qty - order.filled

        for match in candidates:
            match_available = match.qty - match.filled
            trade_qty = min(remaining_qty, match_available)
            if trade_qty <= 0 or trade_price is None or trade_price <= 0:
                continue

            trade_price = match.price

            buy_order = order if is_buy else match
            sell_order = match if is_buy else order

            await self.balance_repo.spend_frozen(db, buy_order.user_id, "RUB", trade_qty * trade_price)
            await self.balance_repo.deposit(db, buy_order.user_id, order.ticker, trade_qty)

            await self.balance_repo.spend_frozen(db, sell_order.user_id, order.ticker, trade_qty)
            await self.balance_repo.deposit(db, sell_order.user_id, "RUB", trade_qty * trade_price)

            order.filled = min(order.qty, order.filled + trade_qty)
            match.filled += min(match.qty, match.filled + trade_qty)

            match.status = update_status(match)
            db.add(Transaction(
                buy_order_id=buy_order.id,
                sell_order_id=sell_order.id,
                ticker=order.ticker,
                amount=trade_qty,
                price=trade_price
            ))
            db.add(match)

            remaining_qty -= trade_qty
            if remaining_qty <= 0:
                break

        if order.price is None and order.filled == 0:
            order.status = OrderStatus.CANCELLED
        else:
            # Обычная логика
            order.status = update_status(order)
        
        db.add(order)

        if is_buy and order.price:
            leftover_rub = (order.qty - order.filled) * order.price
            if leftover_rub > 0:
                await self.balance_repo.unfreeze(db, order.user_id, "RUB", leftover_rub)

        await db.commit()



def update_status(order):
    print(f"order.id={order.id} qty={order.qty} filled={order.filled} -> status={order.status}")
    if order.filled == 0:
        return OrderStatus.NEW
    elif order.filled < order.qty:
        return OrderStatus.PARTIALLY_EXECUTED
    else:
        return OrderStatus.EXECUTED