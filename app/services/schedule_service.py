def get_group_url(
    institute_url: str,
    group_name: str,
) -> str | None:

    print("=" * 60)
    print(f"ИЩЕМ ГРУППУ: {group_name}")
    print(f"СТАРТОВАЯ СТРАНИЦА: {institute_url}")
    print("=" * 60)

    wanted = normalize_text(group_name)

    # Получаем страницу расписания
    url = f"{BASE_URL}/raspisanie/"

    print(f"🌐 Открываем: {url}")

    soup = get_page(url)

    print("✅ Страница расписания загружена")

    # Все ссылки
    links = soup.select("a[href]")

    print(f"🔗 Всего ссылок на странице: {len(links)}")

    # Ищем ссылки институтов
    institutes = []

    for link in links:

        text = normalize_text(
            link.get_text(" ", strip=True)
        )

        href = link.get("href")

        if not text or not href:
            continue

        if "/raspisanie/podrazdelenie/" not in href:
            continue

        if not href.startswith("http"):
            href = BASE_URL + href

        institutes.append(
            {
                "name": text,
                "url": href,
            }
        )

    print(
        f"🏛 Найдено институтов: {len(institutes)}"
    )

    for institute in institutes:

        print()
        print("-" * 60)
        print(
            f"🏛 ПРОВЕРЯЕМ: {institute['name']}"
        )
        print(
            f"🔗 {institute['url']}"
        )

        try:

            institute_soup = get_page(
                institute["url"]
            )

            group_links = institute_soup.select(
                'a[href*="/raspisanie/grup/"]'
            )

            print(
                f"👥 Ссылок на группы: "
                f"{len(group_links)}"
            )

            for link in group_links:

                text = normalize_text(
                    link.get_text(
                        " ",
                        strip=True,
                    )
                )

                href = link.get("href")

                print(
                    f"   → {text} | {href}"
                )

                if text == wanted:

                    if href.startswith("http"):
                        result = href
                    else:
                        result = BASE_URL + href

                    print()
                    print(
                        f"🎯 НАШЛИ ГРУППУ: {result}"
                    )
                    print("=" * 60)

                    return result

        except Exception as e:

            print(
                f"❌ Ошибка: {e}"
            )

    print()
    print(
        f"❌ ГРУППА '{group_name}' НЕ НАЙДЕНА"
    )
    print("=" * 60)

    return None