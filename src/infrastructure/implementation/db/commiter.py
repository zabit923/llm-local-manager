from sqlalchemy.ext.asyncio import AsyncSession


class CommiterImpl:
    def __init__(
        self,
        session: AsyncSession,
    ):
        self.session: AsyncSession = session

    async def commit(self) -> None:
        await self.session.commit()

    async def begin(self) -> None:
        await self.session.begin()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()
