from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from core.schemas.user import User
from repositories import user_repo
from core.database import get_db
from typing import Optional

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if not authorization or not authorization.startswith("TOKEN "):
        raise HTTPException(status_code=401, detail="Use 'TOKEN <key>' format")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty API key")

    user = await user_repo.get_by_api_key(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user


def require_admin(user: User = Depends(get_current_user)):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user