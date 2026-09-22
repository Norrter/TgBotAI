import asyncio

from app.telegram.bot import bot, dp


async def main():
    print("Бот запущен!")
    await dp.start_polling(
        bot,
        polling_timeout=60
    )


if __name__ == "__main__":
    asyncio.run(main())