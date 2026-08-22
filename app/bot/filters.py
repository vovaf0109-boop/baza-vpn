from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from app.config import Settings


class AdminFilter(Filter):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return bool(user and self.settings.is_admin(user.id))
