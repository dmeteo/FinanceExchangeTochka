import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from core.schemas.transaction import Transaction as TransactionSchema
from core.schemas.user import User, UserCreate
from core.database import get_db
from repositories import instrument_repo, user_repo, order_repo, transaction_repo
from core.schemas.order import  L2OrderBook, OrderBookLevel
from core.schemas.instrument import Instrument

router = APIRouter(prefix="/api/v1/public", tags=["public"])

@router.post("/register", response_model=User)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        api_key = f"{uuid.uuid4()}"
        user = await user_repo.create_user(
            db,
            name=user_data.name,
            api_key=api_key,
            role="USER"
        )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Registration failed: {str(e)}"
        )

@router.get("/orderbook/{ticker}", response_model=L2OrderBook)
async def get_orderbook(ticker: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    bids = await order_repo.get_bids(db, ticker, limit)
    asks = await order_repo.get_asks(db, ticker, limit)

    return L2OrderBook(
        bid_levels=[OrderBookLevel(price=o.price, qty=o.qty - o.filled) for o in bids],
        ask_levels=[OrderBookLevel(price=o.price, qty=o.qty - o.filled) for o in asks]
    )

@router.get("/transactions/{ticker}", response_model=list[TransactionSchema], tags=["public"])
async def get_transactions(
    ticker: str,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    transactions = await transaction_repo.get_by_ticker(db, ticker, limit)
    return [TransactionSchema.from_orm(tx) for tx in transactions]

@router.get("/instrument", response_model=list[Instrument])
async def list_instruments(db: AsyncSession = Depends(get_db)):
    instruments = await instrument_repo.get_all(db)
    return [Instrument.model_validate(i) for i in instruments]
