from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.schemas.common import Ok
from core.schemas.balance import BalanceOperation
from core.database import get_db
from core.dependencies import require_admin
from core.schemas.user import User
from core.schemas.instrument import Instrument, InstrumentCreate, InstrumentResponse
from repositories import (
    user_repo,
    instrument_repo,
    balance_repo
)
from uuid import UUID

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.delete("/user/{user_id}", response_model=User)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = await user_repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return user


@router.post("/instrument", response_model=Ok, status_code=status.HTTP_200_OK)
async def add_instrument(
    instrument_in: InstrumentCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(require_admin)
):
    existing = await instrument_repo.get_by_ticker(db, instrument_in.ticker)
    if existing:
        raise HTTPException(status_code=400, detail="Instrument already exists")

    await instrument_repo.create(db=db, obj_in=instrument_in)
    await db.commit()
    return {"success": True}

@router.delete("/instrument/{ticker}", response_model=Ok)
async def delete_instrument(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    instrument = await instrument_repo.get_by_ticker(db, ticker)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    await instrument_repo.delete_by_ticker(db, ticker)
    await db.commit()
    return {"success": True}


@router.post("/balance/deposit", response_model=Ok)
async def deposit(
    payload: BalanceOperation,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = await user_repo.get(db, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    instrument = await instrument_repo.get_by_ticker(db, payload.ticker)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    await balance_repo.deposit(
        db=db,
        user_id=payload.user_id,
        ticker=payload.ticker,
        amount=payload.amount,
    )
    await db.commit()
    return {"success": True}

@router.post("/balance/withdraw", response_model=Ok)
async def withdraw(
    payload: BalanceOperation,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = await user_repo.get(db, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    instrument = await instrument_repo.get_by_ticker(db, payload.ticker)
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    await balance_repo.withdraw(
        db=db,
        user_id=payload.user_id,
        ticker=payload.ticker,
        amount=payload.amount,
    )
    await db.commit()
    return {"success": True}
