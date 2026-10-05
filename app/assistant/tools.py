from datetime import date, datetime, timedelta

from app.database.repositories import (
    get_user_schedule,
    search_lessons,
    search_lessons_by_teacher,
)
from app.services.schedule_loader_service import (
    ensure_week_loaded,
    find_current_lessons,
    find_next_lessons,
)


WEEKDAYS = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "четверг": 3,
    "пятница": 4,
    "суббота": 5,
    "воскресенье": 6,
}

RELATIVE_DAYS = {
    "сегодня": 0,
    "завтра": 1,
    "послезавтра": 2,
}


def parse_date(text: str) -> date | None:
    """
    Преобразование текста в дату.

    Понимает: сегодня / завтра / послезавтра,
    день недели, YYYY-MM-DD и ДД.ММ.ГГГГ.
    """

    text = text.strip().lower()
    today = date.today()

    if text in RELATIVE_DAYS:
        return today + timedelta(days=RELATIVE_DAYS[text])

    if text in WEEKDAYS:
        delta = WEEKDAYS[text] - today.weekday()

        # если день уже прошел,
        # берем следующий такой день
        if delta <= 0:
            delta += 7

        return today + timedelta(days=delta)

    for date_format in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue

    return None


WEEKDAY_NAMES = [
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
]


def describe_day(day: date) -> str:
    """Сегодня / завтра / 12.10.2026 (понедельник)."""

    delta = (day - date.today()).days

    if delta == 0:
        return "сегодня"

    if delta == 1:
        return "завтра"

    return (
        f"{day.strftime('%d.%m.%Y')} "
        f"({WEEKDAY_NAMES[day.weekday()]})"
    )


def lesson_line(lesson) -> str:
    """Одна пара одной строкой — для ответа модели."""

    text = f"{lesson.time} — {lesson.subject}"

    if lesson.groups:
        text += f", группы: {lesson.groups}"

    if lesson.subgroup:
        text += f", подгруппа: {lesson.subgroup}"

    if lesson.teacher:
        text += f", преподаватель: {lesson.teacher}"

    if lesson.room:
        text += f", аудитория: {lesson.room}"

    return text


# ============================================================
# РАСПИСАНИЕ НА ДЕНЬ
# ============================================================

async def get_schedule_for_day(
    group_name: str,
    target_date: str = "сегодня",
):
    """
    Получить расписание группы на конкретную дату.
    """

    target_date = parse_date(target_date)

    if target_date is None:
        return "Не смог определить дату."

    # Если этой недели ещё нет в БД — загружаем её с сайта
    await ensure_week_loaded(
        group_name=group_name,
        target_date=target_date,
    )

    lessons = await get_user_schedule(
        group_name=group_name,
        target_date=target_date,
    )

    if not lessons:
        return (
            f"На {target_date.strftime('%d.%m.%Y')} "
            f"занятий в расписании нет."
        )


    return "\n".join(
        lesson_line(lesson)
        for lesson in lessons
    )



# ============================================================
# ТЕКУЩАЯ И СЛЕДУЮЩАЯ ПАРА
# ============================================================

async def get_next_user_lesson(
    group_name: str,
):
    """
    Получить текущую пару (если она идёт)
    и ближайшую следующую — сегодня или в следующие дни.
    """

    current = await find_current_lessons(group_name)
    upcoming = await find_next_lessons(group_name)

    parts = []

    if current:
        parts.append(
            "Сейчас идёт пара:\n"
            + "\n".join(
                lesson_line(lesson)
                for lesson in current
            )
        )
    else:
        parts.append("Сейчас пары нет.")

    if upcoming:
        parts.append(
            f"Следующая пара — "
            f"{describe_day(upcoming[0].date)}:\n"
            + "\n".join(
                lesson_line(lesson)
                for lesson in upcoming
            )
        )
    else:
        parts.append(
            "В ближайшие недели занятий "
            "в расписании нет."
        )

    return "\n\n".join(parts)



# ============================================================
# ПОИСК ПРЕДМЕТА
# ============================================================

async def find_subject(
    group_name: str,
    subject: str,
):
    """
    Найти занятия группы по названию предмета.
    Например: матанализ, программирование.
    """

    await ensure_week_loaded(
        group_name=group_name,
        target_date=date.today(),
    )

    lessons = await search_lessons(
        group_name,
        subject,
    )


    if not lessons:
        return "Занятий по этому предмету не найдено."


    result = []


    for lesson in lessons:

        text = (
            f"{lesson.date.strftime('%d.%m.%Y')} "
            f"{lesson.time} — "
            f"{lesson.subject}"
        )


        if lesson.teacher:
            text += f", преподаватель: {lesson.teacher}"


        if lesson.room:
            text += f", аудитория: {lesson.room}"


        result.append(text)


    return "\n".join(result[:10])



# ============================================================
# ПОИСК ПРЕПОДАВАТЕЛЯ
# ============================================================

async def find_teacher(
    group_name: str,
    teacher: str,
):
    """
    Найти занятия преподавателя.
    Например: Бучнев, Иванов.
    """


    await ensure_week_loaded(
        group_name=group_name,
        target_date=date.today(),
    )

    lessons = await search_lessons_by_teacher(
        group_name,
        teacher,
    )


    if not lessons:
        return "Занятий этого преподавателя не найдено."


    result = []


    for lesson in lessons:

        text = (
            f"{lesson.date.strftime('%d.%m.%Y')} "
            f"{lesson.time} — "
            f"{lesson.subject}"
        )


        if lesson.teacher:
            text += f", преподаватель: {lesson.teacher}"


        if lesson.room:
            text += f", аудитория: {lesson.room}"


        result.append(text)

    return "\n".join(result[:10])