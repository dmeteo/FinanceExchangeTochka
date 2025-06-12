import asyncio
from celery_app import celery_app
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.repositories.order import OrderRepository
from app.repositories.balance import BalanceRepository
from app.services.order_matching import OrderMatchingService

@celery_app.task(name="tasks.match_order", queue="matching")
def match_order_task(order_id: str):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(_inner(order_id))
    else:
        loop.run_until_complete(_inner(order_id))

async def _inner(order_id: str):
    async with async_session() as db:
        order_repo = OrderRepository()
        balance_repo = BalanceRepository()
        matcher = OrderMatchingService(order_repo, balance_repo)
        order = await order_repo.get(db, order_id)
        if order:
            await matcher.match_order(db, order)
