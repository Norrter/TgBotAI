tools = [

    {
        "type": "function",

        "name": "get_next_user_lesson",

        "description":
            "Получить ближайшую следующую пару студента по его учебной группе. "
            "Использовать когда пользователь спрашивает: какая следующая пара, "
            "что сейчас, куда идти дальше.",

        "parameters": {

            "type": "object",

            "properties": {

                "group_name": {
                    "type": "string",
                }

            },

            "required":[]
        }
    },


    {
        "type": "function",

        "name": "get_schedule_for_day",

        "description":
            "Получить полное расписание учебной группы на конкретную дату. "
            "Использовать когда пользователь спрашивает расписание на сегодня, "
            "завтра или определенный день.",

        "parameters": {

            "type": "object",

            "properties": {

                "group_name": {
                    "type": "string",
                    "description":
                        "Учебная группа студента"
                },

                "target_date": {
                    "type": "string",
                    "description":
                        """
                        Дата расписания.
                        Можно передавать:
                        - YYYY-MM-DD
                        - сегодня
                        - завтра
                        - послезавтра
                        - день недели (понедельник, вторник...)
                        """
                }

            },

            "required": [
            ]
        }
    },


    {
        "type": "function",

        "name": "find_subject",

        "description":
            "Найти все занятия группы по названию предмета. "
            "Использовать когда пользователь спрашивает где, когда или "
            "есть ли пары по определенному предмету.",

        "parameters": {

            "type": "object",

            "properties": {

                "group_name": {
                    "type": "string",
                    "description":
                        "Учебная группа студента"
                },

                "subject": {
                    "type": "string",
                    "description":
                        "Название предмета"
                }

            },

            "required": [
            ]
        }
    },


    {
        "type": "function",

        "name": "find_teacher",

        "description":
            "Найти занятия определенного преподавателя у группы. "
            "Использовать когда пользователь спрашивает про преподавателя.",

        "parameters": {

            "type": "object",

            "properties": {

                "group_name": {
                    "type": "string",
                    "description":
                        "Учебная группа студента"
                },

                "teacher": {
                    "type": "string",
                    "description":
                        "Фамилия или имя преподавателя"
                }

            },

            "required": [
            ]
        }
    }

]