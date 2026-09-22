import asyncio

from app.database.database import engine
from app.database.models import Base


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    await init_db()
    await engine.dispose()

    print("База данных инициализирована!")


if __name__ == "__main__":
    asyncio.run(main())