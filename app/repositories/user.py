from uuid import uuid4
from psycopg2 import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.models.user import User
from core.schemas.user import UserCreate
from .base import BaseRepository

class UserRepository(BaseRepository[User, UserCreate, UserCreate]):
    def __init__(self):
        super().__init__(User)

    async def get_by_api_key(self, db: AsyncSession, api_key: str) -> User | None:
        result = await db.execute(select(User).where(User.api_key == api_key))
        return result.scalars().first()

    async def create_user(
    self,
    db: AsyncSession,
    name: str,
    role: str = "USER",
    api_key: str | None = None
    ) -> User:
        FORBIDDEN_NAMES = {"admin", "root", "support"}
        if name.lower() in FORBIDDEN_NAMES:
            raise ValueError("This username is not allowed")

        existing = await db.execute(select(User).where(User.name == name))
        if existing.scalar():
            raise ValueError("Username already exists")

        if api_key is None:
            api_key = f"{uuid4()}"
            api_key = api_key[:36]

        user = User(
            name=name.strip(),
            role=role,
            api_key=api_key
        )

        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user
        except IntegrityError as e:
            await db.rollback()
            raise ValueError("Database error (possible duplicate api_key)")