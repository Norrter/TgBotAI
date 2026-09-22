import asyncio
from app.assistant.tools import get_next_user_lesson


async def main():

    result = await get_next_user_lesson(
        "АСУб-24-1"
    )

    print(result)


asyncio.run(main())