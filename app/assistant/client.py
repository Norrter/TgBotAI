import os
import json
import asyncio
import logging

from dotenv import load_dotenv
from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    APIError,
    AsyncOpenAI
)

from app.assistant.tools_schema import tools
from app.assistant.tool_executor import execute_tool


load_dotenv()


logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(__name__)


YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")


client = AsyncOpenAI(
    api_key=YANDEX_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_FOLDER_ID,
    timeout=60.0,
    max_retries=0
)


MODEL = f"gpt://{YANDEX_FOLDER_ID}/yandexgpt"


SYSTEM_PROMPT = """

Ты AI-помощник университетского расписания.

Правила:

1. Если пользователь спрашивает расписание -
используй инструменты.

2. Если группа пользователя уже передана сервером -
никогда не спрашивай группу.

3. Всегда используй group_name из контекста сервера.

4. Не придумывай расписание.

5. Если инструмент вернул данные -
используй только эти данные.

6. Отвечай кратко и понятно.

"""


async def create_response(**kwargs):

    """
    Безопасный запрос к API
    с повторными попытками
    """

    attempts = 5


    for attempt in range(1, attempts + 1):

        try:

            return await  client.responses.create(
                **kwargs
            )


        except (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            APIError
        ) as e:


            logger.warning(
                f"Ошибка API. Попытка "
                f"{attempt}/{attempts}: {e}"
            )


            if attempt == attempts:
                raise


            await asyncio.sleep(
                attempt * 2
            )



async def ask_agent(message: str) -> str:


    try:


        response = await create_response(

            model=MODEL,

            input=message,

            tools=tools,

            instructions=SYSTEM_PROMPT
        )



        tool_outputs = []



        for item in response.output:


            if item.type == "function_call":


                arguments = item.arguments


                if isinstance(arguments, str):

                    arguments = json.loads(arguments)



                logger.info(
                    f"Вызов инструмента: "
                    f"{item.name} {arguments}"
                )


                result = await execute_tool(

                    name=item.name,

                    arguments=arguments
                )



                if not isinstance(result, str):

                    result = json.dumps(
                        result,
                        ensure_ascii=False
                    )



                tool_outputs.append(

                    {
                        "type": "function_call_output",

                        "call_id": item.call_id,

                        "output": result
                    }

                )




        # если были tools

        if tool_outputs:


            second_response = await create_response(

                model=MODEL,

                previous_response_id=response.id,

                input=tool_outputs,

                instructions="""

Используй результат инструмента.

Не придумывай данные.

Если есть подгруппы -
обязательно укажи их.

Сделай удобный вывод для студента.

"""
            )


            return second_response.output_text



        return response.output_text



    except Exception as e:


        logger.exception(
            "Ошибка AI агента:"
        )


        return (
            "⚠️ Не удалось обработать запрос.\n"
            "Попробуйте ещё раз через несколько секунд."
        )