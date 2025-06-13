import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories import balance_repo, order_repo
from core.exceptions import InsufficientBalanceException
from core.models.order import Order, OrderStatus
from core.models.transaction import Transaction
from repositories.order import OrderRepository
from repositories.balance import BalanceRepository

class OrderMatchingService:
    def __init__(self, order_repo, balance_repo):
        self.order_repo = order_repo
        self.balance_repo = balance_repo

    async def match_order(self, db: AsyncSession, order: Order):
        if order.status in [OrderStatus.EXECUTED, OrderStatus.CANCELLED]:
            return

        is_buy = order.direction == "BUY"
        remaining_qty = order.qty - order.filled

        opposite_direction = "SELL" if is_buy else "BUY"

        is_market = order.price is None

        if is_market:
            base_query = (
                select(Order)
                .where(
                    Order.ticker == order.ticker,
                    Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                    Order.direction == opposite_direction,
                    Order.price != None
                )
                .order_by(
                    Order.price.asc() if is_buy else Order.price.desc(),
                    Order.created_at.asc(),
                    Order.id.asc()
                )
                .with_for_update()
            )
        else:
            price_cmp = Order.price <= order.price if is_buy else Order.price >= order.price
            base_query = (
                select(Order)
                .where(
                    Order.ticker == order.ticker,
                    Order.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]),
                    Order.direction == opposite_direction,
                    price_cmp
                )
                .order_by(
                    Order.price.asc() if is_buy else Order.price.desc(),
                    Order.created_at.asc(),
                    Order.id.asc()
                )
                .with_for_update()
            )

        result = await db.execute(base_query)
        candidates = result.scalars().all()
        executed = False

        try:
            for match in candidates:
                if remaining_qty <= 0:
                    break

                available_qty = match.qty - match.filled
                if available_qty <= 0:
                    continue

                trade_qty = min(remaining_qty, available_qty)
                trade_price = match.price

                buy_order = order if is_buy else match
                sell_order = match if is_buy else order

                await self.balance_repo.spend_frozen(db, buy_order.user_id, "RUB", trade_qty * trade_price)
                await self.balance_repo.deposit(db, buy_order.user_id, order.ticker, trade_qty)

                await self.balance_repo.spend_frozen(db, sell_order.user_id, order.ticker, trade_qty)
                await self.balance_repo.deposit(db, sell_order.user_id, "RUB", trade_qty * trade_price)

                order.filled += trade_qty
                match.filled += trade_qty
                remaining_qty -= trade_qty
                executed = True

                match.status = update_status(match)
                db.add(match)

            if is_market and order.filled == 0:
                order.status = OrderStatus.CANCELLED
            else:
                order.status = update_status(order)

            db.add(order)

            if not is_market:
                if is_buy:
                    leftover_rub = (order.qty - order.filled) * order.price
                    if leftover_rub > 0:
                        try:
                            await self.balance_repo.unfreeze(db, order.user_id, "RUB", leftover_rub)
                        except Exception as e:
                            logging.warning(f"Unfreeze failed: {e}")
                else:
                    leftover_qty = (order.qty - order.filled)
                    if leftover_qty > 0:
                        try:
                            await self.balance_repo.unfreeze(db, order.user_id, order.ticker, leftover_qty)
                        except Exception as e:
                            logging.warning(f"Unfreeze failed: {e}")

            await db.commit()

        except Exception as e:
            await db.rollback()
            logging.error(f"Order matching failed for order {order.id}: {e}")
            raise

def update_status(order):
    if order.filled == 0:
        return OrderStatus.NEW
    elif order.filled < order.qty:
        return OrderStatus.PARTIALLY_EXECUTED
    else:
        return OrderStatus.EXECUTED

order_matching_service = OrderMatchingService(order_repo, balance_repo)