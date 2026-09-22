import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.istu.edu"
INSTITUTE_URL = "https://www.istu.edu/raspisanie/"
CACHE_FILE = Path("data/groups_cache.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    )
}


def normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def load_page(url: str, retries: int = 5, timeout: int = 60):
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            print()
            print(f"🌐 Загрузка: {url}")
            print(f"   Попытка {attempt}/{retries}")

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=timeout,
            )

            response.raise_for_status()

            print(f"   ✅ Загружено: {len(response.text)} байт")

            return BeautifulSoup(
                response.text,
                "html.parser",
            )

        except requests.RequestException as error:
            last_error = error

            print(f"   ⚠️ Ошибка: {error}")

            if attempt < retries:
                print("   ⏳ Ждём 3 секунды...")
                time.sleep(3)

    raise last_error


def get_institutes():
    print("=" * 60)
    print("🏛 ПОЛУЧАЕМ СПИСОК ИНСТИТУТОВ")
    print("=" * 60)

    soup = load_page(INSTITUTE_URL)

    institutes = {}

    for link in soup.select(
        'a[href*="/raspisanie/podrazdelenie/"]'
    ):
        name = normalize_text(
            link.get_text(" ", strip=True)
        )

        href = link.get("href")

        if not name or not href:
            continue

        url = urljoin(BASE_URL, href)

        institutes[url] = {
            "name": name,
            "url": url,
        }

    institutes = list(institutes.values())

    print()
    print(f"✅ Найдено институтов: {len(institutes)}")

    return institutes


def get_groups_from_institute(institute):
    print()
    print("-" * 60)
    print(f"🏛 Институт: {institute['name']}")
    print(f"🔗 {institute['url']}")
    print("-" * 60)

    soup = load_page(
        institute["url"],
        retries=5,
        timeout=60,
    )

    groups = {}

    for link in soup.select(
        'a[href*="/raspisanie/grup/"]'
    ):
        group_name = normalize_text(
            link.get_text(" ", strip=True)
        )

        href = link.get("href")

        if not group_name or not href:
            continue

        group_url = urljoin(BASE_URL, href)

        groups[group_name] = group_url

    print(f"✅ Найдено групп: {len(groups)}")

    return groups


def save_cache(groups):
    CACHE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with CACHE_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            groups,
            file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    print()
    print("=" * 60)
    print("💾 КЭШ СОХРАНЁН")
    print("=" * 60)
    print(f"📁 Файл: {CACHE_FILE}")
    print(f"👥 Всего групп: {len(groups)}")


def main():
    print()
    print("=" * 60)
    print("🚀 ПОЛНАЯ ЗАГРУЗКА ГРУПП ИРНИТУ")
    print("=" * 60)
    print()

    institutes = get_institutes()

    all_groups = {}

    failed_institutes = []

    for index, institute in enumerate(
        institutes,
        start=1,
    ):
        print()
        print(
            f"📊 ПРОГРЕСС: "
            f"{index}/{len(institutes)}"
        )

        try:
            groups = get_groups_from_institute(
                institute
            )

            before = len(all_groups)

            all_groups.update(groups)

            added = len(all_groups) - before

            print(
                f"📚 Добавлено новых групп: {added}"
            )

        except Exception as error:
            print()
            print(
                f"❌ НЕ УДАЛОСЬ ЗАГРУЗИТЬ: "
                f"{institute['name']}"
            )
            print(f"   Ошибка: {error}")

            failed_institutes.append(
                institute
            )

    save_cache(all_groups)

    print()
    print("=" * 60)
    print("📋 РЕЗУЛЬТАТ")
    print("=" * 60)

    print(f"🏛 Институтов всего: {len(institutes)}")
    print(f"👥 Групп загружено: {len(all_groups)}")
    print(
        f"❌ Институтов с ошибкой: "
        f"{len(failed_institutes)}"
    )

    if failed_institutes:
        print()
        print("⚠️ Не удалось загрузить:")

        for institute in failed_institutes:
            print(
                f"   - {institute['name']}"
            )

    print()
    print(f"💾 Кэш: {CACHE_FILE}")
    print()


if __name__ == "__main__":
    main()