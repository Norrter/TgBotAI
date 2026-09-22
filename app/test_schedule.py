import asyncio
from datetime import date

from app.database.repositories import get_user_schedule


async def main():

    schedule = await get_user_schedule(
        group_name="УКб-23-1",
        target_date=date(2026, 9, 23)
    )

    print("Количество занятий:", len(schedule))

    for lesson in schedule[:5]:
        print(
            lesson.date,
            lesson.time,
            lesson.subject,
            lesson.teacher,
        )


asyncio.run(main())