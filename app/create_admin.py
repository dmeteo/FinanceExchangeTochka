import asyncio
import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.models.user import User
from core.models.base import Base
from core.config import settings  

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
ADMIN_NAME = os.environ.get("ADMIN_NAME")
ADMIN_ROLE = "ADMIN"

engine = create_async_engine(settings.DATABASE_URL, echo=True)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    async with Session() as session:
        result = await session.execute(
            User.__table__.select().where(User.api_key == ADMIN_API_KEY)
        )
        admin = result.scalar_one_or_none()
        if admin:
            print(f"Admin already exists: id={admin.id}, api_key={admin.api_key}")
            return

        admin = User(
            name=ADMIN_NAME,
            role=ADMIN_ROLE,
            api_key=ADMIN_API_KEY,
        )
        session.add(admin)
        await session.commit()
        print(f"Admin created! id={admin.id}, api_key={admin.api_key}")

if __name__ == "__main__":
    asyncio.run(main())