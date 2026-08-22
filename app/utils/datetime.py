from datetime import UTC, datetime

from app.utils.text import plural_ru

MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def format_date_ru(value: datetime) -> str:
    value = ensure_utc(value)
    date = f"{value.day} {MONTHS_RU[value.month]}"
    if value.year != utcnow().year:
        date = f"{date} {value.year}"
    return date


def format_remaining(expires_at: datetime, now: datetime | None = None) -> str:
    now = ensure_utc(now or utcnow())
    expires_at = ensure_utc(expires_at)
    delta = expires_at - now
    seconds = int(delta.total_seconds())
    if seconds <= 0:
        return "0 дней"

    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60

    if days == 0 and hours == 0:
        if minutes < 1:
            return "меньше минуты"
        return f"{minutes} {plural_ru(minutes, 'минута', 'минуты', 'минут')}"

    parts: list[str] = []
    if days:
        parts.append(f"{days} {plural_ru(days, 'день', 'дня', 'дней')}")
    if hours:
        parts.append(f"{hours} {plural_ru(hours, 'час', 'часа', 'часов')}")
    return " ".join(parts)
