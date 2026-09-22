import json
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.istu.edu"
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


def get_page(
    url: str,
    timeout: int = 30,
    retries: int = 3,
) -> BeautifulSoup:
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            print(
                f"🌐 Загрузка: {url} "
                f"(попытка {attempt}/{retries})"
            )

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=timeout,
            )

            response.raise_for_status()

            return BeautifulSoup(
                response.text,
                "html.parser",
            )

        except requests.RequestException as error:
            last_error = error

            print(
                f"⚠️ Ошибка загрузки "
                f"(попытка {attempt}/{retries}): {error}"
            )

            if attempt < retries:
                time.sleep(2)

    raise last_error


def get_institutes(institute_url: str) -> list[dict]:
    print("🔎 Получаем список институтов...")

    soup = get_page(
        institute_url,
        timeout=30,
        retries=3,
    )

    institutes = []

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

        institutes.append({
            "name": name,
            "url": url,
        })

    unique = {}

    for institute in institutes:
        unique[institute["url"]] = institute

    institutes = list(unique.values())

    print(f"✅ Найдено институтов: {len(institutes)}")

    return institutes


def find_groups_on_page(
    page_url: str,
) -> dict[str, str]:
    soup = get_page(
        page_url,
        timeout=30,
        retries=2,
    )

    groups = {}

    for link in soup.select(
        'a[href*="/raspisanie/grup/"]'
    ):
        name = normalize_text(
            link.get_text(" ", strip=True)
        )

        href = link.get("href")

        if not name or not href:
            continue

        groups[name] = urljoin(BASE_URL, href)

    return groups


def save_groups_cache(groups: dict[str, str]) -> None:
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
        )

    print(
        f"💾 Кэш групп сохранён: "
        f"{CACHE_FILE} "
        f"({len(groups)} групп)"
    )


def load_groups_cache() -> dict[str, str]:
    if not CACHE_FILE.exists():
        return {}

    try:
        with CACHE_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            groups = json.load(file)

        print(
            f"📦 Загружен кэш групп: "
            f"{len(groups)} групп"
        )

        return groups

    except (json.JSONDecodeError, OSError) as error:
        print(
            f"⚠️ Не удалось прочитать кэш групп: "
            f"{error}"
        )

        return {}


def build_groups_cache(
    institute_url: str,
) -> dict[str, str]:
    print("🔎 Начинаем сбор всех групп...")

    institutes = get_institutes(institute_url)

    all_groups = {}

    for index, institute in enumerate(
        institutes,
        start=1,
    ):
        print(
            f"🔎 [{index}/{len(institutes)}] "
            f"{institute['name']}"
        )

        try:
            groups = find_groups_on_page(
                institute["url"]
            )

            print(
                f"   Найдено групп: {len(groups)}"
            )

            all_groups.update(groups)

        except requests.RequestException as error:
            print(
                f"⚠️ Не удалось загрузить "
                f"{institute['url']}: {error}"
            )

            # Один институт не должен ломать
            # поиск остальных.
            continue

        except Exception as error:
            print(
                f"⚠️ Ошибка обработки "
                f"{institute['url']}: {error}"
            )

            continue

    save_groups_cache(all_groups)

    print(
        f"✅ Всего собрано групп: "
        f"{len(all_groups)}"
    )

    return all_groups


def get_group_url(
    institute_url: str,
    group_name: str,
) -> str | None:
    target = normalize_text(group_name)

    print(
        f"🔎 Ищем группу '{target}'..."
    )

    # 1. Сначала проверяем кэш.
    groups = load_groups_cache()

    if target in groups:
        print(
            f"⚡ Группа найдена в кэше: "
            f"{groups[target]}"
        )

        return groups[target]

    # 2. Если кэша нет или группы в нём нет,
    #    строим его заново.
    print(
        "📥 Группы в кэше нет. "
        "Обновляем кэш..."
    )

    try:
        groups = build_groups_cache(
            institute_url
        )

    except requests.RequestException as error:
        print(
            f"❌ Не удалось получить "
            f"данные с сайта: {error}"
        )

        return None

    if target in groups:
        print(
            f"✅ Группа найдена: "
            f"{groups[target]}"
        )

        return groups[target]

    print(
        f"❌ Группа '{target}' "
        f"не найдена"
    )

    return None


def get_groups(
    institute_url: str,
) -> list[str]:
    groups = load_groups_cache()

    if not groups:
        groups = build_groups_cache(
            institute_url
        )

    return sorted(groups.keys())