from app.assistant.client import ask_agent
from app.assistant.context import set_group



async def process_message(
    message: str,
    group: str | None,
):

    context = ""

    if group:
        context = f"""
Пользователь зарегистрирован в группе: {group}

ВАЖНО:
- Никогда не спрашивай название группы.
- Всегда используй эту группу при вызове инструментов.
"""

    prompt = f"""
Ты помощник университетского расписания.

{context}

Сообщение пользователя:
{message}

Правила:
- Если вопрос про расписание используй инструменты.
- Если есть группа в контексте, передавай её в group_name.
- Не проси пользователя повторно назвать группу.
- Не придумывай расписание.
"""

    answer = await ask_agent(prompt)

    return answer