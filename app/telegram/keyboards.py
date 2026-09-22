from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Сегодня",
                    callback_data="schedule_today"
                ),
                InlineKeyboardButton(
                    text="➡️ Завтра",
                    callback_data="schedule_tomorrow"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📆 Выбрать дату",
                    callback_data="choose_date"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏭ Следующая пара",
                    callback_data="next_lesson"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔎 Найти занятие",
                    callback_data="search_subject"
                ),
                InlineKeyboardButton(
                    text="👨‍🏫 Преподаватель",
                    callback_data="search_teacher"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Настройки",
                    callback_data="settings"
                ),
                InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="help"
                ),
            ],
        ]
    )


def settings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Моя группа",
                    callback_data="change_group"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_to_menu"
                ),
            ],
        ]
    )


def date_keyboard(target_date: date | None = None) -> InlineKeyboardMarkup:
    if target_date is None:
        target_date = date.today()

    keyboard = []

    for i in range(7):
        day = target_date + timedelta(days=i)

        keyboard.append([
            InlineKeyboardButton(
                text=f"{day.strftime('%d.%m')} ({day.strftime('%a')})",
                callback_data=f"date_{day.isoformat()}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data="back_to_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def week_navigation_keyboard(
    target_date: date
) -> InlineKeyboardMarkup:

    previous_day = target_date - timedelta(days=1)
    next_day = target_date + timedelta(days=1)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀️ Предыдущий день",
                    callback_data=f"day_{previous_day.isoformat()}"
                ),
                InlineKeyboardButton(
                    text="Следующий день ▶️",
                    callback_data=f"day_{next_day.isoformat()}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="back_to_menu"
                ),
            ],
        ]
    )