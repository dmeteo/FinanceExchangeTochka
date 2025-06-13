import logging
from uuid import UUID, uuid4
from typing import Union

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import InsufficientBalanceException
from core.schemas.common import Ok
from core.schemas.order import LimitOrder, LimitOrderBody, MarketOrder, MarketOrderBody, CreateOrderResponse, OrderResponse
from core.models.order import Order, OrderStatus
from repositories.order import OrderRepository
from repositories.balance import BalanceRepository
from repositories.instrument import InstrumentRepository
from tasks.match_order import match_order_task
from services.order_matching import order_matching_service
from core.dependencies import get_db, get_current_user

router = APIRouter(prefix="/api/v1/order", tags=["order"])

order_repo = OrderRepository()
balance_repo = BalanceRepository()
instrument_repo = InstrumentRepository()


@router.get("", response_model=list[OrderResponse])
async def get_orders(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    orders = await order_repo.get_user_orders(db, user.id)
    return [_build_order_response(order) for order in orders]

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    order = await order_repo.get(db, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return _build_order_response(order)

def _build_order_response(order):
    if order.price is not None:
        return LimitOrder(
            id=order.id,
            status=order.status,
            user_id=order.user_id,
            timestamp=order.created_at,
            filled=order.filled,
            body=LimitOrderBody(
                direction=order.direction,
                ticker=order.ticker,
                qty=max(order.qty - order.filled, 0),
                price=order.price
            )
        )
    else:
        return MarketOrder(
            id=order.id,
            status=order.status,
            user_id=order.user_id,
            timestamp=order.created_at,
            filled=order.filled,
            body=MarketOrderBody(
                direction=order.direction,
                ticker=order.ticker,
                qty=max(order.qty - order.filled, 0)
            )
        )

@router.delete("/{order_id}", response_model=Ok)
async def cancel_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    order = await order_repo.get(db, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.price is None:
        raise HTTPException(status_code=400, detail="Market orders cannot be cancelled")

    if order.status != OrderStatus.NEW:
        raise HTTPException(status_code=400, detail="Only NEW limit orders can be cancelled")

    remaining_qty = order.qty - order.filled
    if remaining_qty > 0:
        if order.direction == "BUY":
            rub_to_return = remaining_qty * order.price
            await balance_repo.unfreeze(db, order.user_id, "RUB", rub_to_return)
        else:
            await balance_repo.unfreeze(db, order.user_id, order.ticker, remaining_qty)

    await order_repo.cancel(db, order)
    return {"success": True}


@router.post("", response_model=CreateOrderResponse)
async def create_order(
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
    ):
    try:
        if "price" in body:
            parsed = LimitOrderBody(**body)
            if parsed.qty <= 0 or parsed.price <= 0:
                raise HTTPException(status_code=422, detail="qty and price must be > 0")
        else:
            parsed = MarketOrderBody(**body)
            if parsed.qty <= 0:
                raise HTTPException(status_code=422, detail="qty must be > 0")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    ticker = parsed.ticker.upper()
    instrument = await instrument_repo.get_by_ticker(db, ticker)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    order_id = uuid4()

    try:
        if isinstance(parsed, LimitOrderBody):
            if parsed.direction == "BUY":
                await balance_repo.freeze(db, user.id, "RUB", parsed.qty * parsed.price)
            else:
                await balance_repo.freeze(db, user.id, ticker, parsed.qty)

            order = Order(
                id=order_id,
                user_id=user.id,
                status=OrderStatus.NEW,
                direction=parsed.direction,
                ticker=ticker,
                qty=parsed.qty,
                price=parsed.price,
                filled=0
            )
        else: 
            order = Order(
                id=order_id,
                user_id=user.id,
                status=OrderStatus.NEW,
                direction=parsed.direction,
                ticker=ticker,
                qty=parsed.qty,
                price=None,
                filled=0
            )

        db.add(order)
        await db.commit()
        await order_matching_service.match_order(db, order)
        return {"success": True, "order_id": order.id}

    except InsufficientBalanceException as e:
        raise HTTPException(status_code=400, detail=str(e))

