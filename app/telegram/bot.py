import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from app.telegram.handlers import router


load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Прокси только для запросов к Telegram (остальные запросы идут напрямую).
# Примеры: socks5://127.0.0.1:1080, http://127.0.0.1:8080,
#          socks5://user:password@host:port
# Если переменная не задана или пустая — бот подключается без прокси.
TELEGRAM_PROXY = (os.getenv("TELEGRAM_PROXY") or "").strip() or None

session = AiohttpSession(proxy=TELEGRAM_PROXY) if TELEGRAM_PROXY else None

bot = Bot(
    token=TOKEN,
    session=session,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)
dp = Dispatcher()

dp.include_router(router)
