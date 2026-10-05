import html
import re
from datetime import date, timedelta

from app.assistant.service import process_message
from app.assistant.speech import (
    MAX_VOICE_BYTES,
    MAX_VOICE_SECONDS,
    recognize_speech,
)
from app.assistant.tools import describe_day
from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.database.repositories import (
    get_or_create_user,
    update_user_group,
    get_user_schedule,
    search_lessons,
    search_lessons_by_teacher,
)

from app.parser.group_parser import get_group_url
from app.services.schedule_loader_service import (
    ensure_week_loaded,
    find_current_lessons,
    find_next_lessons,
)

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

    # Если расписания нет — пробуем загрузить неделю с сайта
    if not schedule:
        loaded = await ensure_week_loaded(
            group_name=group_name,
            target_date=target_date,
        )

        if loaded:
            schedule = await get_user_schedule(
                group_name=group_name,
                target_date=target_date,
            )

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
# ТЕКСТОВЫЕ КОМАНДЫ (меню, помощь, настройки)
# ============================================================
# Эти фразы обрабатываются сразу, без обращения к AI.
# Сравнивается всё сообщение целиком (без регистра,
# знаков препинания и эмодзи), поэтому обычные вопросы
# вроде "какие пары завтра" сюда не попадают.

MENU_PHRASES = {
    "меню",
    "menu",
    "главное меню",
    "в меню",
    "в главное меню",
    "на главную",
    "главная",
    "домой",
    "назад",
    "открой меню",
    "открыть меню",
    "покажи меню",
    "показать меню",
    "открой главное меню",
    "покажи главное меню",
    "вернись в меню",
    "вернуться в меню",
    "старт",
    "начать",
}

HELP_PHRASES = {
    "помощь",
    "help",
    "справка",
    "помоги",
    "что ты умеешь",
    "что умеешь",
    "что ты можешь",
    "как пользоваться",
    "как пользоваться ботом",
}

SETTINGS_PHRASES = {
    "настройки",
    "settings",
    "открой настройки",
    "покажи настройки",
    "моя группа",
    "сменить группу",
    "изменить группу",
    "поменять группу",
}

HELP_TEXT = (
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


def normalize_phrase(text: str | None) -> str:
    if not text:
        return ""

    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text)

    return " ".join(text.split())


def phrase_in(phrases: set[str]):
    return F.text.func(
        lambda text: normalize_phrase(text) in phrases
    )


async def send_main_menu(message: Message):
    user = await get_user(message)

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

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


async def send_help(message: Message):
    await message.answer(
        HELP_TEXT,
        reply_markup=main_menu(),
    )


async def send_settings(message: Message):
    user = await get_user(message)

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

    await message.answer(
        text,
        reply_markup=settings_menu(),
    )


async def answer_with_ai(
    message: Message,
    text: str,
):
    """Отправляет вопрос в AI-помощник и отвечает пользователю."""

    user = await get_user(message)

    try:
        await message.answer(
            "⏳ Обрабатываю ваш запрос..."
        )
    except Exception as e:
        print("Telegram send error:", e)
        return

    answer = await process_message(
        text,
        user.group_name
    )

    await message.answer(answer)


async def handle_free_text(
    message: Message,
    text: str,
):
    """
    Общая обработка запроса в свободной форме —
    одинаковая для текста и распознанного голоса.
    """

    phrase = normalize_phrase(text)

    if phrase in MENU_PHRASES:
        await send_main_menu(message)

    elif phrase in HELP_PHRASES:
        await send_help(message)

    elif phrase in SETTINGS_PHRASES:
        await send_settings(message)

    else:
        await answer_with_ai(message, text)


@router.message(phrase_in(MENU_PHRASES))
async def menu_text_handler(
    message: Message,
    state: FSMContext,
):
    await state.clear()
    await send_main_menu(message)


@router.message(phrase_in(HELP_PHRASES))
async def help_text_handler(
    message: Message,
    state: FSMContext,
):
    await state.clear()
    await send_help(message)


@router.message(phrase_in(SETTINGS_PHRASES))
async def settings_text_handler(
    message: Message,
    state: FSMContext,
):
    await state.clear()
    await send_settings(message)


# ============================================================
# ГОЛОСОВЫЕ СООБЩЕНИЯ
# ============================================================
# Голосовое распознаётся через Yandex SpeechKit и дальше
# обрабатывается так же, как обычный текстовый запрос.

@router.message(F.voice)
async def voice_message_handler(
    message: Message,
    state: FSMContext,
):
    voice = message.voice

    if (
        voice.duration > MAX_VOICE_SECONDS
        or (voice.file_size or 0) > MAX_VOICE_BYTES
    ):
        await message.answer(
            "🎤 Голосовое сообщение слишком длинное.\n\n"
            f"Запишите вопрос короче {MAX_VOICE_SECONDS} секунд "
            "или напишите его текстом."
        )
        return

    status = await message.answer(
        "🎤 Распознаю голосовое сообщение..."
    )

    try:
        audio = await message.bot.download(voice)
        text = await recognize_speech(audio.read())

    except Exception as e:
        print(f"❌ Ошибка распознавания речи: {e}")

        await status.edit_text(
            "❌ Не удалось распознать голосовое сообщение.\n\n"
            "Попробуйте ещё раз или напишите вопрос текстом."
        )
        return

    if not text:
        await status.edit_text(
            "🤔 Не удалось разобрать речь.\n\n"
            "Попробуйте сказать чётче или напишите вопрос текстом."
        )
        return

    await status.edit_text(
        f"🎤 Вы сказали: {html.escape(text)}"
    )

    await state.clear()

    await handle_free_text(message, text)



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

    current = await find_current_lessons(user.group_name)
    upcoming = await find_next_lessons(user.group_name)

    text = ""

    if current:
        text += "▶️ Сейчас идёт\n\n"

        for lesson in current:
            text += format_lesson(lesson) + "\n"

    if upcoming:
        text += (
            "⏭ Следующая пара — "
            f"{describe_day(upcoming[0].date)}\n\n"
        )

        for lesson in upcoming:
            text += format_lesson(lesson) + "\n"

    else:
        text += (
            "⏭ В ближайшие недели занятий "
            "в расписании нет."
        )

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

@router.message(UserStates.waiting_for_group, F.text)
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


@router.message(UserStates.waiting_for_subject, F.text)
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

    await ensure_week_loaded(
        group_name=user.group_name,
        target_date=date.today(),
    )

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


@router.message(UserStates.waiting_for_teacher, F.text)
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

    await ensure_week_loaded(
        group_name=user.group_name,
        target_date=date.today(),
    )

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

    text = HELP_TEXT

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
    await answer_with_ai(message, message.text)
