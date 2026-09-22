from datetime import date, datetime, timedelta

from app.database.repositories import (
    get_user_schedule,
    get_next_lesson,
    search_lessons,
    search_lessons_by_teacher,
)


def parse_date(text: str) -> date | None:
    """
    Преобразование текста в дату
    """

    today = date.today()

    days = {
        "понедельник": 0,
        "вторник": 1,
        "среда": 2,
        "четверг": 3,
        "пятница": 4,
        "суббота": 5,
        "воскресенье": 6,
    }


    if text == "сегодня":
        return today


    if text == "завтра":
        return today + timedelta(days=1)


    if text == "послезавтра":
        return today + timedelta(days=2)


    if text.lower() in days:

        target_weekday = days[text.lower()]

        delta = (
            target_weekday -
            today.weekday()
        )

        # если день уже прошел,
        # берем следующий такой день

        if delta <= 0:
            delta += 7

        return today + timedelta(days=delta)


    try:
        return datetime.strptime(
            text,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        pass


    try:
        return datetime.strptime(
            text,
            "%d.%m.%Y"
        ).date()

    except ValueError:
        return None

# ============================================================
# РАСПИСАНИЕ НА ДЕНЬ
# ============================================================

async def get_schedule_for_day(
    group_name: str,
    target_date: str,
):
    """
    Получить расписание группы на конкретную дату.
    """

    # обработка человеческих дат
    if target_date == "сегодня":
        target_date = date.today()

    elif target_date == "завтра":
        target_date = date.today() + timedelta(days=1)

    elif target_date == "послезавтра":
        target_date = date.today() + timedelta(days=2)

    else:
        try:
            parsed_date = parse_date(target_date)

            if parsed_date is None:
                return "Не смог определить дату."

            target_date = parsed_date

        except ValueError:
            try:
                target_date = datetime.strptime(
                    target_date,
                    "%d.%m.%Y"
                ).date()

            except ValueError:
                return "Не смог определить дату."


    lessons = await get_user_schedule(
        group_name=group_name,
        target_date=target_date,
    )

    if not lessons:
        return "На этот день расписания нет."


    result = []

    for lesson in lessons:

        text = (
            f"{lesson.time} — "
            f"{lesson.subject}"
        )
        if lesson.groups:
            text += (
                f", группы: "
                f"{lesson.groups}"
            )

        if lesson.subgroup:
            text += (
                f", подгруппа: "
                f"{lesson.subgroup}"
            )

        if lesson.teacher:
            text += (
                f", преподаватель: "
                f"{lesson.teacher}"
            )

        if lesson.room:
            text += (
                f", аудитория: "
                f"{lesson.room}"
            )

        result.append(text)


    return "\n".join(result)



# ============================================================
# СЛЕДУЮЩАЯ ПАРА
# ============================================================

async def get_next_user_lesson(
    group_name: str,
):
    """
    Получить ближайшую пару пользователя.
    """

    lesson = await get_next_lesson(
        group_name
    )


    if lesson is None:
        return "Сегодня больше занятий нет."


    result = (
        f"{lesson.time} — "
        f"{lesson.subject}"
    )

    if lesson.groups:
        text += (
            f", группы: "
            f"{lesson.groups}"
        )

    if lesson.subgroup:
        text += (
            f", подгруппа: "
            f"{lesson.subgroup}"
        )


    if lesson.teacher:
        result += (
            f", преподаватель: "
            f"{lesson.teacher}"
        )


    if lesson.room:
        result += (
            f", аудитория: "
            f"{lesson.room}"
        )


    return result



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

    print("RESULT:", result)
    return "\n".join(result[:10])