from sqlalchemy import select
import asyncio

from app.database.database import async_session
from app.database.models import Schedule


async def main():
    async with async_session() as session:

        result = await session.execute(
            select(Schedule)
            .where(
                Schedule.groups.ilike("%УКб%")
            )
            .limit(20)
        )

        lessons = result.scalars().all()

        for lesson in lessons:
            print(
                lesson.date,
                lesson.groups,
                lesson.week,
                lesson.subject
            )


asyncio.run(main())