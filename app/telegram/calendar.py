from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta


def date_keyboard(target_date: date | None = None):

    if target_date is None:
        target_date = date.today()

    keyboard = []

    # текущая дата и ближайшие 7 дней
    for i in range(7):
        day = target_date + timedelta(days=i)

        keyboard.append([
            InlineKeyboardButton(
                text=f"{day.strftime('%d.%m')} ({day.strftime('%a')})",
                callback_data=f"date_{day.isoformat()}"
            )
        ])

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )