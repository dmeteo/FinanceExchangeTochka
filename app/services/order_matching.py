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
            Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
            Order.direction != order.direction,
        )

        if order.price is not None:
            price_condition = (
                Order.price <= order.price if is_buy else Order.price >= order.price
            )
            base_query = base_query.where(price_condition)

        base_query = base_query.with_for_update()
        base_query = base_query.order_by(
            Order.price.asc() if is_buy else Order.price.desc()
        )

        result = await db.execute(base_query)
        candidates = result.scalars().all()
        remaining_qty = order.qty
        
        print(f"[DEBUG] order: id={order.id} dir={order.direction} status={order.status} filled={order.filled} qty={order.qty}")
        print(f"[DEBUG] найдено кандидатов: {len(candidates)}")
        for match in candidates:
            print(f"[MATCHING] Checking: order={order.id} ({order.direction}) with candidate={match.id} ({match.direction}), "
                    f"order.qty={order.qty}, match.qty={match.qty}, "
                    f"order.filled={order.filled}, match.filled={match.filled}")
            available_qty = match.qty - match.filled
            trade_qty = min(available_qty, remaining_qty)
            trade_price = match.price if match.price is not None else order.price

            if trade_qty <= 0 or trade_price is None:
                continue

            buy_order = order if is_buy else match
            sell_order = match if is_buy else order
            buyer_id = buy_order.user_id
            seller_id = sell_order.user_id

            await self.balance_repo.spend_frozen(db, buyer_id, "RUB", trade_qty * trade_price)
            await self.balance_repo.deposit(db, buyer_id, order.ticker, trade_qty)

            await self.balance_repo.spend_frozen(db, seller_id, order.ticker, trade_qty)
            await self.balance_repo.deposit(db, seller_id, "RUB", trade_qty * trade_price)

            transaction = Transaction(
                buy_order_id=buy_order.id,
                sell_order_id=sell_order.id,
                ticker=order.ticker,
                amount=trade_qty,
                price=trade_price
            )

            order.filled += trade_qty
            match.filled += trade_qty

            match.status = update_status(match)

            db.add(transaction)
            db.add(match)
            print(f"match: {match.id}, filled={match.filled}, status={match.status}")

            remaining_qty -= trade_qty
            if remaining_qty <= 0:
                break

        order.status = update_status(order)

        db.add(order)
        await db.commit()


def update_status(order):
    print(f"order.id={order.id} qty={order.qty} filled={order.filled} -> status={order.status}")
    if order.filled == 0:
        return OrderStatus.NEW
    elif order.filled < order.qty:
        return OrderStatus.PARTIALLY_EXECUTED
    else:
        return OrderStatus.EXECUTED