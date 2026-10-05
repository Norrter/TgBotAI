"""Поиск рабочего публичного SOCKS5-прокси для Telegram Bot API.

Запуск из корня проекта:

    python -m app.find_proxy          # найти и показать рабочие прокси
    python -m app.find_proxy --save   # записать самый быстрый в .env (TELEGRAM_PROXY)

Публичные прокси живут недолго: если бот перестал отвечать,
запустите скрипт с --save ещё раз и перезапустите бота.
"""

import argparse
import asyncio
import random
import re
import time
from pathlib import Path

import aiohttp
import requests
from aiohttp_socks import ProxyConnector


# Открытые списки SOCKS5-прокси (формат: IP:PORT в каждой строке).
SOURCES = [
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
]

CHECK_URL = "https://api.telegram.org"
CHECK_ATTEMPTS = 2       # сколько раз подряд прокси должен ответить
TIMEOUT = 8              # секунд на одну попытку
CONCURRENCY = 150        # одновременных проверок
MAX_CANDIDATES = 3000    # максимум адресов для проверки
WANTED = 3               # сколько рабочих прокси найти перед остановкой

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
ENV_KEY = "TELEGRAM_PROXY"

PROXY_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})\b")


def load_candidates() -> list[str]:
    """Скачивает списки и возвращает адреса без повторов."""
    candidates: list[str] = []
    seen: set[str] = set()

    for url in SOURCES:
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"Не удалось загрузить список {url}: {error}")
            continue

        chunk = []
        for ip, port in PROXY_RE.findall(response.text):
            address = f"{ip}:{port}"
            if address not in seen:
                seen.add(address)
                chunk.append(address)

        random.shuffle(chunk)
        candidates.extend(chunk)
        print(f"Загружено {len(chunk)} адресов из {url}")

    return candidates[:MAX_CANDIDATES]


async def check(address: str) -> float | None:
    """Возвращает среднее время ответа Telegram через прокси или None."""
    total = 0.0

    for _ in range(CHECK_ATTEMPTS):
        started = time.monotonic()
        try:
            connector = ProxyConnector.from_url(f"socks5://{address}", rdns=True)
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
            ) as session:
                async with session.get(CHECK_URL, allow_redirects=False) as response:
                    if response.status >= 500:
                        return None
        except Exception:
            return None
        total += time.monotonic() - started

    return total / CHECK_ATTEMPTS


async def find(candidates: list[str], wanted: int = WANTED) -> list[tuple[float, str]]:
    """Проверяет адреса параллельно, останавливается после `wanted` рабочих."""
    semaphore = asyncio.Semaphore(CONCURRENCY)
    found: list[tuple[float, str]] = []

    async def run(address: str):
        async with semaphore:
            return address, await check(address)

    tasks = [asyncio.create_task(run(address)) for address in candidates]

    try:
        for future in asyncio.as_completed(tasks):
            address, seconds = await future
            if seconds is None:
                continue
            found.append((seconds, address))
            print(f"  работает: socks5://{address} ({seconds:.1f} с)")
            if len(found) >= wanted:
                break
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    return sorted(found)


def save_to_env(proxy_url: str, path: Path = ENV_PATH) -> None:
    """Записывает TELEGRAM_PROXY в .env, не трогая остальные строки."""
    line = f"{ENV_KEY}={proxy_url}"
    text = ""
    if path.exists():
        with path.open(encoding="utf-8", newline="") as file:
            text = file.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    pattern = re.compile(rf"^{ENV_KEY}=[^\r\n]*", re.MULTILINE)

    if pattern.search(text):
        text = pattern.sub(lambda _: line, text, count=1)
    else:
        if text and not text.endswith(("\n", "\r")):
            text += newline
        text += line + newline

    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--save",
        action="store_true",
        help="записать самый быстрый прокси в .env",
    )
    args = parser.parse_args()

    candidates = load_candidates()
    if not candidates:
        print("Списки прокси не загрузились — проверьте интернет.")
        raise SystemExit(1)

    print(f"Проверяю {len(candidates)} адресов, это может занять пару минут...")
    found = asyncio.run(find(candidates))

    if not found:
        print("Рабочих прокси не нашлось. Попробуйте запустить ещё раз позже.")
        raise SystemExit(1)

    best = f"socks5://{found[0][1]}"
    print(f"\nСамый быстрый: {best}")

    if args.save:
        save_to_env(best)
        print(f"Записано в {ENV_PATH.name}: {ENV_KEY}={best}")
        print("Перезапустите бота, чтобы он подхватил новый прокси.")
    else:
        print(f"Чтобы использовать его, добавьте в .env строку:\n{ENV_KEY}={best}")


if __name__ == "__main__":
    main()
