from app.assistant.tools import (
    get_schedule_for_day,
    get_next_user_lesson,
    find_subject,
    find_teacher,
)




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
    arguments: dict,
    group: str | None = None,
):

    tool = TOOLS_MAP.get(name)

    if not tool:
        return "Инструмент не найден"

    # Если модель не передала группу —
    # берём группу пользователя.
    if not arguments.get("group_name"):

        if not group:
            return (
                "Группа пользователя не указана. "
                "Попроси указать её в настройках."
            )

        arguments["group_name"] = group

    return await tool(**arguments)
