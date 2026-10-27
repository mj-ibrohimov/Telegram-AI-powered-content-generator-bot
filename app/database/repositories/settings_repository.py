from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import BotSetting

AUTO_POSTING_KEY = "auto_posting_enabled"


class SettingsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> str | None:
        result = await self.session.execute(select(BotSetting).where(BotSetting.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

    async def set(self, key: str, value: str) -> None:
        result = await self.session.execute(select(BotSetting).where(BotSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting is None:
            self.session.add(BotSetting(key=key, value=value))
        else:
            setting.value = value
        await self.session.commit()

    async def is_auto_posting_enabled(self) -> bool:
        value = await self.get(AUTO_POSTING_KEY)
        return value != "false"

    async def set_auto_posting_enabled(self, enabled: bool) -> None:
        await self.set(AUTO_POSTING_KEY, "true" if enabled else "false")
