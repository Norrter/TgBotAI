from datetime import date, timedelta, datetime

from sqlalchemy import select

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
# CURRENT / NEXT LESSON
# ============================================================

# Пара в ИРНИТУ длится 1 час 30 минут
LESSON_DURATION = timedelta(minutes=90)

# На сколько дней вперёд искать ближайшую пару
NEXT_LESSON_SEARCH_DAYS = 14


def lesson_start(lesson: Schedule) -> datetime:
    """Дата и время начала пары."""

    hour, minute = map(
        int,
        lesson.time.split(":")
    )

    return datetime(
        lesson.date.year,
        lesson.date.month,
        lesson.date.day,
        hour,
        minute,
    )


async def get_current_lessons(
    group_name: str,
    now: datetime | None = None,
) -> list[Schedule]:
    """
    Пары, которые идут прямо сейчас.

    Список, потому что у разных подгрупп
    в одно время могут быть разные занятия.
    """

    now = now or datetime.now()

    schedule = await get_user_schedule(
        group_name,
        now.date(),
    )

    return [
        lesson
        for lesson in schedule
        if lesson_start(lesson)
        <= now
        < lesson_start(lesson) + LESSON_DURATION
    ]


async def get_next_lessons(
    group_name: str,
    now: datetime | None = None,
    days_ahead: int = NEXT_LESSON_SEARCH_DAYS,
) -> list[Schedule]:
    """
    Ближайшие пары, которые ещё не начались.

    Сначала проверяется сегодняшний день, затем
    завтра и следующие дни (до days_ahead дней вперёд).
    Возвращаются все пары ближайшего времени начала.
    """

    now = now or datetime.now()

    for offset in range(days_ahead + 1):

        day = now.date() + timedelta(days=offset)

        schedule = await get_user_schedule(
            group_name,
            day,
        )

        upcoming = [
            lesson
            for lesson in schedule
            if lesson_start(lesson) > now
        ]

        if upcoming:

            nearest = lesson_start(upcoming[0])

            return [
                lesson
                for lesson in upcoming
                if lesson_start(lesson) == nearest
            ]

    return []



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