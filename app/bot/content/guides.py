GUIDES: dict[str, str] = {
    "general": (
        "📲 Как подключиться\n"
        "\n"
        "1. Установи Happ.\n"
        "2. Открой приложение.\n"
        "3. Нажми добавление подписки.\n"
        "4. Вставь свою ссылку.\n"
        "5. Обнови подписку.\n"
        "6. Выбери сервер.\n"
        "7. Нажми подключиться."
    ),
    # Заготовки под отдельные платформы — без переписывания бота.
    "ios": "",
    "android": "",
    "windows": "",
    "macos": "",
}


def guide_text(platform: str = "general") -> str:
    text = GUIDES.get(platform) or GUIDES["general"]
    return text or GUIDES["general"]
