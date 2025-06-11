from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.dependencies import get_current_user
from repositories import balance_repo
from typing import Dict

router = APIRouter(prefix="/api/v1/balance", tags=["balance"])

@router.get("/", response_model=dict)
async def get_balances(
    user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    balances = await balance_repo.get_user_balances(db=db, user_id=user.id)
    return {b.ticker: b.amount for b in balances}