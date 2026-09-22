from app.assistant.tools import (
    get_schedule_for_day,
    get_next_user_lesson,
    find_subject,
    find_teacher,
)

from app.assistant.context import get_group



TOOLS_MAP = {

    "get_schedule_for_day":
        get_schedule_for_day,

    "get_next_user_lesson":
        get_next_user_lesson,

    "find_subject":
        find_subject,

    "find_teacher":
        find_teacher,
}



async def execute_tool(
    name: str,
    arguments: dict
):

    tool = TOOLS_MAP.get(name)


    if not tool:
        return "Инструмент не найден"



    group = get_group()


    if group:

        arguments["group_name"] = group



    result = await tool(**arguments)


    return result