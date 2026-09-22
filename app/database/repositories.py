from datetime import date, timedelta, datetime

from sqlalchemy import update, delete, select

from app.database.database import async_session
from app.database.models import Schedule, User


# 14.09.2026 — нечётная неделя по расписанию ИРНИТУ
ODD_WEEK_START = date(2026, 9, 14)


def get_week_type(target_date: date) -> str:
    days_difference = (
        target_date - ODD_WEEK_START
    ).days

    weeks_difference = days_difference // 7

    if weeks_difference % 2 == 0:
        return "odd"

    return "even"


# ============================================================
# USERS
# ============================================================

async def get_or_create_user(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> User:

    async with async_session() as session:

        result = await session.execute(
            select(User)
            .where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()


        if user is None:

            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )

            session.add(user)

            await session.commit()
            await session.refresh(user)


        return user



async def update_user_university(
    telegram_id: int,
    university: str,
):

    async with async_session() as session:

        await session.execute(
            update(User)
            .where(
                User.telegram_id == telegram_id
            )
            .values(
                university=university
            )
        )

        await session.commit()



async def update_user_group(
    telegram_id: int,
    group_name: str,
) -> None:

    async with async_session() as session:

        result = await session.execute(
            select(User)
            .where(
                User.telegram_id == telegram_id
            )
        )

        user = result.scalar_one_or_none()


        if user:

            user.group_name = group_name

            await session.commit()



# ============================================================
# SCHEDULE SAVE
# ============================================================


async def save_schedule(
    schedule_data: list[dict],
) -> None:


    async with async_session() as session:


        for lesson in schedule_data:


            schedule = Schedule(

                date=lesson["date"],

                time=lesson["time"],

                week=lesson["week"],


                subject=lesson["subject"],


                lesson_type=lesson.get(
                    "type"
                ),


                teacher=lesson.get(
                    "teacher"
                ),


                groups=lesson.get(
                    "group"
                ),


                # ВАЖНО:
                # сохраняем подгруппу
                subgroup=lesson.get(
                    "subgroup"
                ),


                room=lesson.get(
                    "room"
                ),

            )


            session.add(schedule)



        await session.commit()



# ============================================================
# DELETE
# ============================================================


async def delete_schedule_for_group(
    group_name: str,
) -> None:


    async with async_session() as session:


        await session.execute(
            delete(Schedule)
            .where(
                Schedule.groups.ilike(
                    f"%{group_name}%"
                )
            )
        )


        await session.commit()



# ============================================================
# GET SCHEDULE
# ============================================================


async def get_user_schedule(
    group_name: str,
    target_date: date,
) -> list[Schedule]:


    week_type = get_week_type(
        target_date
    )


    async with async_session() as session:


        result = await session.execute(

            select(Schedule)

            .where(

                Schedule.date == target_date,


                Schedule.groups.ilike(
                    f"%{group_name}%"
                ),


                Schedule.week.in_(
                    [
                        "all",
                        week_type
                    ]
                ),

            )

        )


        schedule = list(
            result.scalars().all()
        )


        schedule.sort(
            key=lambda lesson: (
                int(
                    lesson.time.split(":")[0]
                ),
                int(
                    lesson.time.split(":")[1]
                ),
            )
        )


        return schedule



# ============================================================
# NEXT LESSON
# ============================================================


async def get_next_lesson(
    group_name: str,
):

    now = datetime.now()


    schedule = await get_user_schedule(
        group_name,
        date.today(),
    )


    for lesson in schedule:


        hour, minute = map(
            int,
            lesson.time.split(":")
        )


        lesson_time = now.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )


        if lesson_time > now:

            return lesson



    return None



# ============================================================
# SEARCH
# ============================================================


async def search_lessons(
    group_name: str,
    subject: str,
) -> list[Schedule]:


    async with async_session() as session:


        result = await session.execute(

            select(Schedule)

            .where(

                Schedule.groups.ilike(
                    f"%{group_name}%"
                ),

                Schedule.subject.ilike(
                    f"%{subject}%"
                ),

            )

            .order_by(
                Schedule.date,
                Schedule.time,
            )

        )


        return list(
            result.scalars().all()
        )




async def search_lessons_by_teacher(
    group_name: str,
    teacher: str,
) -> list[Schedule]:


    async with async_session() as session:


        result = await session.execute(

            select(Schedule)

            .where(

                Schedule.groups.ilike(
                    f"%{group_name}%"
                ),


                Schedule.teacher.ilike(
                    f"%{teacher}%"
                ),

            )

            .order_by(
                Schedule.date,
                Schedule.time,
            )

        )


        return list(
            result.scalars().all()
        )



# ============================================================
# CHECK WEEK
# ============================================================


async def has_schedule_for_week(
    group_name: str,
    week_start: date,
) -> bool:


    week_end = (
        week_start
        + timedelta(days=6)
    )


    async with async_session() as session:


        result = await session.execute(

            select(Schedule.id)

            .where(

                Schedule.groups.ilike(
                    f"%{group_name}%"
                ),


                Schedule.date >= week_start,


                Schedule.date <= week_end,

            )

            .limit(1)

        )


        return (
            result.scalar_one_or_none()
            is not None
        )