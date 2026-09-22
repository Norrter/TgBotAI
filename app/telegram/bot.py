import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.telegram.handlers import router


load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)
dp = Dispatcher()

dp.include_router(router)