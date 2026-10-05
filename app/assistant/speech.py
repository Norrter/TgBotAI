"""Распознавание голосовых сообщений через Yandex SpeechKit."""

import json
import os

import aiohttp
from dotenv import load_dotenv


load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

# Ограничения синхронного распознавания SpeechKit
MAX_VOICE_SECONDS = 30
MAX_VOICE_BYTES = 1024 * 1024


class SpeechRecognitionError(Exception):
    pass


async def recognize_speech(
    audio: bytes,
    lang: str = "ru-RU",
) -> str:
    """
    Преобразует голосовое сообщение Telegram (OGG/Opus) в текст.

    Возвращает пустую строку, если речь не распознана.
    """

    if not YANDEX_API_KEY:
        raise SpeechRecognitionError(
            "Не задан YANDEX_API_KEY"
        )

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
    ) as session:

        async with session.post(
            STT_URL,
            params={
                "lang": lang,
                "topic": "general",
                "format": "oggopus",
            },
            headers={
                "Authorization": f"Api-Key {YANDEX_API_KEY}",
            },
            data=audio,
        ) as response:

            body = await response.text()

            if response.status != 200:
                raise SpeechRecognitionError(
                    f"SpeechKit вернул {response.status}: "
                    f"{body[:300]}"
                )

    try:
        result = json.loads(body).get("result")
    except json.JSONDecodeError as error:
        raise SpeechRecognitionError(
            f"Некорректный ответ SpeechKit: {body[:300]}"
        ) from error

    return (result or "").strip()
