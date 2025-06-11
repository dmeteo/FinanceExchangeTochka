from uuid import uuid4
from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.order import LimitOrderBody, MarketOrderBody, CreateOrderResponse
from core.models.order import Order, OrderStatus
from repositories.order import OrderRepository
from repositories.balance import BalanceRepository
from repositories.instrument import InstrumentRepository
from services.order_matching import OrderMatchingService
from tasks.match_order import match_order_task
from core.dependencies import get_db, get_current_user

router = APIRouter(prefix="/api/v1/order", tags=["order"])

order_repo = OrderRepository()
balance_repo = BalanceRepository()
instrument_repo = InstrumentRepository()

@router.post("/", response_model=CreateOrderResponse)
async def create_order(
    body: Union[LimitOrderBody, MarketOrderBody],
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    ticker = body.ticker.upper()

    # 1. Проверка инструмента
    instrument = await instrument_repo.get_by_ticker(db, ticker)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    order_id = uuid4()
    matcher = OrderMatchingService(order_repo, balance_repo)

    if isinstance(body, LimitOrderBody):
        # 2. Проверка баланса и резерв
        if body.direction == "BUY":
            total = body.qty * body.price
            rub_balance = await balance_repo.get_balance(db, user.id, "RUB")
            if not rub_balance or rub_balance.amount < total:
                raise HTTPException(status_code=400, detail="Insufficient RUB balance")
            rub_balance.amount -= total
        else:
            asset_balance = await balance_repo.get_balance(db, user.id, ticker)
            if not asset_balance or asset_balance.amount < body.qty:
                raise HTTPException(status_code=400, detail="Insufficient asset balance")
            asset_balance.amount -= body.qty

        # 3. Сохранение лимитной заявки
        order = Order(
            id=order_id,
            user_id=user.id,
            status=OrderStatus.NEW,
            direction=body.direction,
            ticker=ticker,
            qty=body.qty,
            price=body.price,
            filled=0
        )

        db.add(order)
        await db.commit()

        # 4. Передаём в matching engine (Celery)
        match_order_task.delay(str(order.id))

        return {"success": True, "order_id": order.id}

    else:
        # Market Order — исполняется немедленно, не попадает в orderbook
        order = Order(
            id=order_id,
            user_id=user.id,
            status=OrderStatus.NEW,
            direction=body.direction,
            ticker=ticker,
            qty=body.qty,
            price=None,
            filled=0
        )

        await matcher.match_order(db, order)

        if order.filled == 0:
            raise HTTPException(status_code=400, detail="Market order could not be executed")

        db.add(order)
        await db.commit()

        return {"success": True, "order_id": order.id}
