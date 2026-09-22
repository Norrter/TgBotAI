import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
import re


MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def parse_date(date_text: str) -> date:
    date_text = date_text.replace("\xa0", " ")

    parts = date_text.split(",")

    if len(parts) != 2:
        raise ValueError(
            f"Не удалось разобрать дату: {date_text}"
        )

    day, month = parts[1].strip().split()

    return date(
        year=date.today().year,
        month=MONTHS[month.lower()],
        day=int(day),
    )


def clean_text(element):
    if not element:
        return None

    text = element.get_text(" ", strip=True)

    return text if text else None


def get_schedule(
    group_url: str,
    target_date: date | None = None,
) -> list[dict]:
    """
    Получает расписание группы на неделю,
    в которую входит target_date.

    Например:
    target_date = 21.09.2026
    → запрашивается:
    /raspisanie/grup/478021/21.09.2026/
    """

    if target_date is None:
        target_date = date.today()

    # Понедельник нужной недели.
    monday = target_date - timedelta(
        days=target_date.weekday()
    )

    # Убираем последний "/" и добавляем дату.
    group_url = group_url.rstrip("/")

    schedule_url = (
        f"{group_url}/"
        f"{monday.strftime('%d.%m.%Y')}/"
    )

    print(f"Загружаем расписание: {schedule_url}")

    response = requests.get(
        schedule_url,
        timeout=120,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    schedule = []

    for day in soup.select(".sch-list-day"):
        day_header = day.select_one(
            ".sch-list-day-header"
        )

        if not day_header:
            continue

        date_text = day_header.get_text(
            " ",
            strip=True,
        )

        for lesson in day.select(".sch-list-item"):
            time = lesson.select_one(
                ".sch-list-item-time-inner"
            )

            if not time:
                continue

            time_text = time.get_text(
                " ",
                strip=True,
            )

            for week_block in lesson.select(
                ".sch-list-item-week"
            ):
                classes = week_block.get(
                    "class",
                    [],
                )

                if "week-even" in classes:
                    week = "even"

                elif "week-odd" in classes:
                    week = "odd"

                elif "week-all" in classes:
                    week = "all"

                else:
                    week = "unknown"

                for card in week_block.select(
                    ".schcls-item"
                ):
                    if "schcls-empty" in card.get(
                        "class",
                        [],
                    ):
                        continue

                    subject = card.select_one(
                        ".schcls-item-name"
                    )

                    lesson_type = card.select_one(
                        ".schcls-item-distype"
                    )

                    teacher = card.select_one(
                        ".schcls-item-prepod"
                    )

                    group = card.select_one(".schcls-item-group")
                    group_text = clean_text(group)

                    subgroup = None

                    if group_text:
                        match = re.search(
                            r"подгруппа\s+(\d+)",
                            group_text,
                            re.IGNORECASE,
                        )
                        if match:
                            subgroup = match.group(1)

                    room = card.select_one(".schcls-item-aud")

                    lesson_data = {
                        "date": parse_date(date_text),
                        "time": time_text,
                        "week": week,
                        "subject": clean_text(subject),
                        "type": clean_text(lesson_type),
                        "teacher": clean_text(teacher),
                        "group": clean_text(group),
                        "room": clean_text(room),
                        "subgroup": subgroup,
                    }
                    print("ГРУППА:", clean_text(group))

                    if lesson_data not in schedule:
                        schedule.append(
                            lesson_data
                        )

    return schedule