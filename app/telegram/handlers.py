from datetime import date, datetime
from app.assistant.service import process_message
from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.database.repositories import (
    get_or_create_user,
    update_user_group,
    get_user_schedule,
    get_next_lesson,
    search_lessons,
    search_lessons_by_teacher,
)

from app.parser.group_parser import get_group_url
from app.services.schedule_loader_service import ensure_week_loaded

from app.telegram.keyboards import (
    main_menu,
    settings_menu,
    date_keyboard,
    week_navigation_keyboard,
)


router = Router()


# ============================================================
# НАСТРОЙКИ
# ============================================================

INSTITUTE_URL = "https://www.istu.edu/raspisanie/"


# ============================================================
# FSM СОСТОЯНИЯ
# ============================================================



class UserStates(StatesGroup):

    waiting_for_group = State()

    waiting_for_subject = State()

    waiting_for_teacher = State()

    waiting_for_date = State()

    current_schedule_date = State()


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def get_user(message: Message):
    return await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )


async def get_user_from_callback(callback: CallbackQuery):
    return await get_or_create_user(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )


async def get_group_for_user(message: Message):
    user = await get_user(message)

    if not user.group_name:
        await message.answer(
            "👥 У тебя пока не указана группа.\n\n"
            "Зайди в ⚙️ Настройки → 👥 Моя группа "
            "и введи название своей группы."
        )
        return None

    return user.group_name


def format_lesson(lesson) -> str:
    text = f"🕐 {lesson.time}\n"
    text += f"📚 {lesson.subject}\n"

    if lesson.lesson_type:
        text += f"📝 Тип: {lesson.lesson_type}\n"

    if lesson.teacher:
        text += f"👨‍🏫 Преподаватель: {lesson.teacher}\n"

    if lesson.subgroup:
        text += f"👥 Подгруппа: {lesson.subgroup}\n"

    if lesson.room:
        text += f"🚪 Аудитория: {lesson.room}\n"

    return text

# ============================================================
# ПОКАЗ РАСПИСАНИЯ
# ============================================================

async def show_schedule(
    message: Message,
    state: FSMContext,
    target_date: date,
    user=None,
):
    if user is None:
        user = await get_user(message)

    if not user.group_name:
        await message.answer(
            "👥 Сначала укажи свою группу.\n\n"
            "Открой ⚙️ Настройки → 👥 Моя группа."
        )
        return

    group_name = user.group_name

    # Сначала ищем расписание в БД
    schedule = await get_user_schedule(
        group_name=group_name,
        target_date=target_date,
    )

    # Если расписания нет — пробуем загрузить с сайта
    if not schedule:
        try:
            group_url = get_group_url(
                institute_url=INSTITUTE_URL,
                group_name=group_name,
            )

            if group_url:
                await ensure_week_loaded(
                    group_name=group_name,
                    target_date=target_date,
                )

                schedule = await get_user_schedule(
                    group_name=group_name,
                    target_date=target_date,
                )

        except Exception as e:
            print(f"Ошибка загрузки расписания: {e}")

    await state.update_data(
        current_date=target_date.isoformat()
    )

    if not schedule:
        await message.answer(
            f"📅 {target_date.strftime('%d.%m.%Y')}\n\n"
            f"👥 Группа: {group_name}\n\n"
            "Расписание на этот день не найдено.",
            reply_markup=week_navigation_keyboard(target_date),
        )
        return

    weekday = target_date.strftime("%A")

    weekdays = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота",
        "Sunday": "Воскресенье",
    }

    weekday = weekdays.get(weekday, weekday)

    text = (
        f"📅 {weekday}, "
        f"{target_date.strftime('%d.%m.%Y')}\n"
        f"👥 Группа: {group_name}\n\n"
    )

    for lesson in schedule:
        text += format_lesson(lesson)
        text += "\n"

    await message.answer(
        text,
        reply_markup=week_navigation_keyboard(target_date),
    )


# ============================================================
# START
# ============================================================

@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    user = await get_user(message)

    if user.group_name:
        text = (
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            f"👥 Твоя группа: {user.group_name}\n\n"
            "Выбери действие:"
        )
    else:
        text = (
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "Я помогу посмотреть расписание.\n\n"
            "⚠️ Для начала укажи свою группу.\n"
            "Например: АСУб-26-1"
        )

    await message.answer(
        text,
        reply_markup=main_menu(),
    )



# ============================================================
# СЕГОДНЯ
# ============================================================

@router.callback_query(F.data == "schedule_today")
async def today_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    user = await get_user_from_callback(callback)

    await show_schedule(
        callback.message,
        state,
        date.today(),
        user=user,
    )


# ============================================================
# ЗАВТРА
# ============================================================

@router.callback_query(F.data == "schedule_tomorrow")
async def tomorrow_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    from datetime import timedelta

    user = await get_user_from_callback(callback)

    await show_schedule(
        callback.message,
        state,
        date.today() + timedelta(days=1),
        user=user,
    )


# ============================================================
# ВЫБОР ДАТЫ
# ============================================================

@router.callback_query(F.data == "choose_date")
async def choose_date_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    await callback.message.answer(
        "📆 Выбери дату:",
        reply_markup=date_keyboard(),
    )


# ============================================================
# ВЫБРАННАЯ ДАТА
# ============================================================

@router.callback_query(F.data.startswith("date_"))
async def selected_date_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    date_string = callback.data.replace("date_", "")

    try:
        selected_date = date.fromisoformat(date_string)
    except ValueError:
        await callback.message.answer(
            "❌ Не удалось определить дату."
        )
        return

    user = await get_user_from_callback(callback)

    await show_schedule(
        callback.message,
        state,
        selected_date,
        user=user,
    )


# ============================================================
# ПЕРЕХОД МЕЖДУ ДНЯМИ
# ============================================================

@router.callback_query(F.data.startswith("day_"))
async def change_day_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    date_string = callback.data.replace("day_", "")

    try:
        selected_date = date.fromisoformat(date_string)
    except ValueError:
        await callback.message.answer(
            "❌ Ошибка даты."
        )
        return

    user = await get_user_from_callback(callback)

    await show_schedule(
        callback.message,
        state,
        selected_date,
        user=user,
    )


# ============================================================
# СЛЕДУЮЩАЯ ПАРА
# ============================================================

@router.callback_query(F.data == "next_lesson")
async def next_lesson_handler(
    callback: CallbackQuery,
):
    await callback.answer()

    user = await get_user_from_callback(callback)

    if not user.group_name:
        await callback.message.answer(
            "👥 Сначала укажи свою группу."
        )
        return

    lesson = await get_next_lesson(
        group_name=user.group_name
    )

    if lesson is None:
        await callback.message.answer(
            "⏭ На сегодня больше пар нет."
        )
        return

    text = (
        "⏭ Следующая пара\n\n"
        f"📚 {lesson.subject}\n"
        f"🕐 {lesson.time}\n"
    )

    if lesson.lesson_type:
        text += f"📝 {lesson.lesson_type}\n"

    if lesson.teacher:
        text += f"👨‍🏫 {lesson.teacher}\n"

    if lesson.room:
        text += f"🚪 {lesson.room}\n"

    await callback.message.answer(text)


# ============================================================
# НАСТРОЙКИ
# ============================================================

@router.callback_query(F.data == "settings")
async def settings_handler(
    callback: CallbackQuery,
):
    await callback.answer()

    user = await get_user_from_callback(callback)

    if user.group_name:
        text = (
            "⚙️ Настройки\n\n"
            f"👥 Текущая группа: {user.group_name}"
        )
    else:
        text = (
            "⚙️ Настройки\n\n"
            "👥 Группа пока не указана."
        )

    await callback.message.answer(
        text,
        reply_markup=settings_menu(),
    )


# ============================================================
# ИЗМЕНИТЬ ГРУППУ
# ============================================================

@router.callback_query(F.data == "change_group")
async def change_group_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    await state.set_state(
        UserStates.waiting_for_group
    )

    await callback.message.answer(
        "👥 Введи название своей группы.\n\n"
        "Например:\n"
        "АСУб-26-1\n\n"
        "Можно просто отправить название группы сообщением."
    )


# ============================================================
# СОХРАНЕНИЕ ГРУППЫ
# ============================================================

@router.message(UserStates.waiting_for_group)
async def group_input_handler(
    message: Message,
    state: FSMContext,
):
    group_name = message.text.strip()

    if not group_name:
        await message.answer(
            "❌ Название группы не может быть пустым.\n\n"
            "Например:\n"
            "АСУб-26-1"
        )
        return

    # Сообщение о начале поиска
    status_message = await message.answer(
        f"🔎 Ищу группу...\n\n"
        f"👥 {group_name}\n\n"
        "⏳ Проверяю список институтов и групп..." \
        "Это может занять некоторое время, так как я обращаюсь к сайту ИРНИТУ."
    )

    try:
        # Ищем группу на сайте ИРНИТУ
        group_url = get_group_url(
            institute_url=INSTITUTE_URL,
            group_name=group_name,
        )

    except Exception as e:
        print(f"❌ Ошибка поиска группы: {e}")

        await status_message.edit_text(
            f"❌ Не удалось выполнить поиск.\n\n"
            f"👥 Группа: {group_name}\n\n"
            "Возможно, сайт ИРНИТУ временно недоступен.\n"
            "Попробуй ещё раз через некоторое время."
        )
        return

    # Группа не найдена
    if not group_url:
        await status_message.edit_text(
            f"❌ Группа не найдена.\n\n"
            f"Ты ввёл: {group_name}\n\n"
            "Проверь название группы и попробуй ещё раз.\n\n"
            "Например:\n"
            "АСУб-26-1"
        )
        return

    # Группа найдена
    await status_message.edit_text(
        f"✅ Группа найдена!\n\n"
        f"👥 {group_name}\n\n"
        "💾 Сохраняю группу..."
    )

    # Сохраняем группу
    await update_user_group(
        telegram_id=message.from_user.id,
        group_name=group_name,
    )

    await state.clear()

    await status_message.edit_text(
        f"✅ Группа сохранена!\n\n"
        f"👥 {group_name}\n\n"
        "Теперь можно смотреть расписание.",
        reply_markup=main_menu(),
    )


# ============================================================
# ПОИСК ПРЕДМЕТА
# ============================================================

@router.callback_query(F.data == "search_subject")
async def search_subject_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    user = await get_user_from_callback(callback)

    if not user.group_name:
        await callback.message.answer(
            "👥 Сначала укажи свою группу."
        )
        return

    await state.set_state(
        UserStates.waiting_for_subject
    )

    await callback.message.answer(
        "🔎 Введи название предмета.\n\n"
        "Например:\n"
        "Программирование"
    )


@router.message(UserStates.waiting_for_subject)
async def subject_input_handler(
    message: Message,
    state: FSMContext,
):
    subject = message.text.strip()

    user = await get_user(message)

    if not user.group_name:
        await state.clear()

        await message.answer(
            "👥 Сначала укажи группу.",
            reply_markup=main_menu(),
        )
        return

    lessons = await search_lessons(
        group_name=user.group_name,
        subject=subject,
    )

    await state.clear()

    if not lessons:
        await message.answer(
            f"🔎 По запросу {subject} "
            "занятий не найдено.",
            reply_markup=main_menu(),
        )
        return

    text = (
        "🔎 Результаты поиска\n\n"
        f"Запрос: {subject}\n\n"
    )

    for lesson in lessons[:15]:
        text += (
            f"📅 {lesson.date.strftime('%d.%m.%Y')}\n"
            f"🕐 {lesson.time}\n"
            f"📚 {lesson.subject}\n"
        )

        if lesson.teacher:
            text += f"👨‍🏫 Преподаватель: {lesson.teacher}\n"

        if lesson.room:
            text += f"🚪 Аудитория: {lesson.room}\n"

        text += "\n"

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


# ============================================================
# ПОИСК ПРЕПОДАВАТЕЛЯ
# ============================================================

@router.callback_query(F.data == "search_teacher")
async def search_teacher_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    user = await get_user_from_callback(callback)

    if not user.group_name:
        await callback.message.answer(
            "👥 Сначала укажи группу."
        )
        return

    await state.set_state(
        UserStates.waiting_for_teacher
    )

    await callback.message.answer(
        "👨‍🏫 Введи фамилию преподавателя.\n\n"
        "Например:\n"
        "Иванов"
    )


@router.message(UserStates.waiting_for_teacher)
async def teacher_input_handler(
    message: Message,
    state: FSMContext,
):
    teacher = message.text.strip()

    user = await get_user(message)

    if not user.group_name:
        await state.clear()

        await message.answer(
            "👥 Сначала укажи группу.",
            reply_markup=main_menu(),
        )
        return

    lessons = await search_lessons_by_teacher(
        group_name=user.group_name,
        teacher=teacher,
    )

    await state.clear()

    if not lessons:
        await message.answer(
            f"👨‍🏫 Занятий преподавателя "
            f"{teacher} не найдено.",
            reply_markup=main_menu(),
        )
        return

    text = (
        "👨‍🏫 Занятия преподавателя\n\n"
        f"Поиск: {teacher}\n\n"
    )

    for lesson in lessons[:15]:
        text += (
            f"📅 {lesson.date.strftime('%d.%m.%Y')}\n"
            f"🕐 {lesson.time}\n"
            f"📚 {lesson.subject}\n"
        )

        if lesson.room:
            text += f"🚪 Аудитория: {lesson.room}\n"

        text += "\n"

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


# ============================================================
# ПОМОЩЬ
# ============================================================

@router.callback_query(F.data == "help")
async def help_handler(
    callback: CallbackQuery,
):
    await callback.answer()

    text = (
        "ℹ️ Как пользоваться ботом\n\n"
        "📅 Сегодня — расписание на сегодня.\n\n"
        "➡️ Завтра — расписание на завтра.\n\n"
        "📆 Выбрать дату — расписание "
        "на конкретный день.\n\n"
        "⏭ Следующая пара — ближайшее "
        "занятие сегодня.\n\n"
        "🔎 Найти занятие — поиск предмета "
        "в расписании.\n\n"
        "👨‍🏫 Преподаватель — поиск занятий "
        "по преподавателю.\n\n"
        "⚙️ Настройки — изменить группу.\n\n"
        "Для работы боту достаточно указать "
        "только свою группу."
    )

    await callback.message.answer(
        text,
        reply_markup=main_menu(),
    )


# ============================================================
# НАЗАД В МЕНЮ
# ============================================================

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(
    callback: CallbackQuery,
    state: FSMContext,
):
    await callback.answer()

    await state.clear()

    user = await get_user_from_callback(callback)

    if user.group_name:
        text = (
            "🏠 Главное меню\n\n"
            f"👥 Группа: {user.group_name}"
        )
    else:
        text = (
            "🏠 Главное меню\n\n"
            "👥 Группа не указана."
        )

    await callback.message.answer(
        text,
        reply_markup=main_menu(),
    )



# ============================================================
# AI ASSISTANT
# ============================================================

@router.message(
    F.text,
    StateFilter(None),
)
async def ai_message_handler(
    message: Message,
):

    user = await get_user(message)

    try:
        await message.answer(
            "⏳ Обрабатываю ваш запрос..."
        )
    except Exception as e:
        print("Telegram send error:", e)
        return


    answer = await process_message(
        message.text,
        user.group_name
    )


    await message.answer(answer)



@router.message(
    F.text,
    StateFilter(None),
)
async def ai_message_handler(
    message: Message,
):

    user = await get_user(message)

    status = await message.answer(
        "⏳ Обрабатываю ваш запрос..."
    )

    try:

        answer = await process_message(
            message.text,
            user.group_name
        )

        await status.edit_text(answer)

    except Exception as e:

        print("AI ERROR:", e)

        await status.edit_text(
            "❌ Не удалось обработать запрос. Попробуйте ещё раз."
        )