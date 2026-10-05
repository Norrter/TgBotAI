import asyncio
from datetime import date, datetime, timedelta

from app.database.repositories import (
    get_current_lessons,
    get_next_lessons,
    has_schedule_for_week,
    save_schedule,
)

from app.parser.group_parser import get_group_url
from app.parser.schedule_parser import get_schedule


INSTITUTE_URL = "https://www.istu.edu/raspisanie/"


async def ensure_week_loaded(
    group_name: str,
    target_date: date,
    group_url: str | None = None,
) -> int:
    """
    Проверяет наличие расписания недели в БД.

    Если неделя уже загружена:
        ничего не делает.

    Если нет:
        - загружает расписание с сайта;
        - сохраняет пары вместе с подгруппами.
    """

    # Определяем понедельник текущей недели
    week_start = (
        target_date
        - timedelta(days=target_date.weekday())
    )


    # Проверяем есть ли эта неделя в БД
    already_loaded = await has_schedule_for_week(
        group_name=group_name,
        week_start=week_start,
    )


    if already_loaded:
        print(
            f"✅ Неделя {week_start} уже загружена"
        )

        return 0



    print(
        f"⚠️ Неделя {week_start} отсутствует в БД"
    )


    # Если URL группы не передали — находим его сами
    # (сначала в кэше, затем на сайте).
    # Запросы к сайту блокирующие, поэтому выполняем
    # их в отдельном потоке, чтобы бот не зависал.
    if not group_url:

        try:

            group_url = await asyncio.to_thread(
                get_group_url,
                INSTITUTE_URL,
                group_name,
            )

        except Exception as e:

            print(
                f"❌ Ошибка поиска группы: {e}"
            )

            return 0


    if not group_url:

        print(
            f"❌ Не найден URL группы {group_name}"
        )

        return 0



    print(
        f"📥 Загружаем расписание:\n{group_url}"
    )


    try:

        schedule = await asyncio.to_thread(
            get_schedule,
            group_url=group_url,
            target_date=week_start,
        )


    except Exception as e:

        print(
            f"❌ Ошибка парсинга расписания: {e}"
        )

        return 0



    if not schedule:

        print(
            "⚠️ Расписание не найдено"
        )

        return 0



    # Сохраняем расписание
    # вместе с subgroup
    await save_schedule(
        schedule
    )


    print(
        f"✅ Загружено занятий: {len(schedule)}"
    )


    # вывод для проверки
    subgroups = [
        lesson.get("subgroup")
        for lesson in schedule
        if lesson.get("subgroup")
    ]


    if subgroups:

        print(
            f"👥 Найдены подгруппы: {set(subgroups)}"
        )


    return len(schedule)


# На сколько недель вперёд (кроме текущей)
# искать ближайшую пару
NEXT_LESSON_WEEKS_AHEAD = 2


async def find_current_lessons(
    group_name: str,
    now: datetime | None = None,
):
    """
    Пары, которые идут прямо сейчас.
    При необходимости загружает текущую неделю с сайта.
    """

    now = now or datetime.now()

    await ensure_week_loaded(
        group_name=group_name,
        target_date=now.date(),
    )

    return await get_current_lessons(
        group_name,
        now,
    )


async def find_next_lessons(
    group_name: str,
    now: datetime | None = None,
):
    """
    Ближайшие будущие пары.

    Ищет сначала на текущей неделе, затем на следующих,
    подгружая каждую неделю с сайта, если её нет в БД.
    """

    now = now or datetime.now()

    week_start = (
        now.date()
        - timedelta(days=now.weekday())
    )

    for week in range(NEXT_LESSON_WEEKS_AHEAD + 1):

        monday = week_start + timedelta(weeks=week)

        await ensure_week_loaded(
            group_name=group_name,
            target_date=monday,
        )

        # Ищем до воскресенья этой недели включительно
        days_ahead = (
            monday
            + timedelta(days=6)
            - now.date()
        ).days

        lessons = await get_next_lessons(
            group_name,
            now,
            days_ahead,
        )

        if lessons:
            return lessons

    return []
