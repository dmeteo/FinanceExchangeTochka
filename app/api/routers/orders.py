from uuid import UUID, uuid4
from typing import Union

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas.common import Ok
from core.schemas.order import LimitOrderBody, MarketOrderBody, CreateOrderResponse, OrderResponse
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


@router.get("/", response_model=list[OrderResponse])
async def get_orders(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    return await order_repo.get_by_user(db, user.id)

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    order = await order_repo.get(db, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.delete("/{order_id}", response_model=Ok)
async def cancel_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    order = await order_repo.get(db, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]:
        raise HTTPException(status_code=400, detail="Only NEW or PARTIALLY_EXECUTED orders can be cancelled")

    await order_repo.cancel(db, order)
    return {"success": True}


@router.post("/", response_model=CreateOrderResponse)
async def create_order(
    body: Union[LimitOrderBody, MarketOrderBody],
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    ticker = body.ticker.upper()

    instrument = await instrument_repo.get_by_ticker(db, ticker)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    order_id = uuid4()
    matcher = OrderMatchingService(order_repo, balance_repo)

    if isinstance(body, LimitOrderBody):
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

        match_order_task.delay(str(order.id))

        return {"success": True, "order_id": order.id}

    else:
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
