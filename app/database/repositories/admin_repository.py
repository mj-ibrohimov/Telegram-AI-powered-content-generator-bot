from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Admin


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_admin(self, telegram_user_id: int) -> bool:
        result = await self.session.execute(
            select(Admin).where(Admin.telegram_user_id == telegram_user_id, Admin.is_active.is_(True))
        )
        return result.scalar_one_or_none() is not None

    async def get_by_telegram_id(self, telegram_user_id: int) -> Admin | None:
        result = await self.session.execute(select(Admin).where(Admin.telegram_user_id == telegram_user_id))
        return result.scalar_one_or_none()

    async def upsert(self, telegram_user_id: int, username: str | None) -> Admin:
        admin = await self.get_by_telegram_id(telegram_user_id)
        if admin is None:
            admin = Admin(telegram_user_id=telegram_user_id, username=username, is_active=True)
            self.session.add(admin)
        else:
            admin.username = username
            admin.is_active = True
        await self.session.commit()
        return admin
