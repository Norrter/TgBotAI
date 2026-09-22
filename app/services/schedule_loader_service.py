from datetime import date, timedelta

from app.database.repositories import (
    has_schedule_for_week,
    save_schedule,
)

from app.parser.schedule_parser import get_schedule


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


    # Если URL группы нет
    if not group_url:

        print(
            "❌ Не передан URL группы"
        )

        return 0



    print(
        f"📥 Загружаем расписание:\n{group_url}"
    )


    try:

        schedule = get_schedule(
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