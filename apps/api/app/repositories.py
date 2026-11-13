from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]):
        self.session = session
        self.model = model

    async def create(self, **values: object) -> ModelT:
        record = self.model(**values)
        self.session.add(record)
        await self.session.flush()
        return record

    async def get(self, record_id: UUID) -> ModelT | None:
        return await self.session.get(self.model, record_id)

    async def list(self, *, limit: int = 100) -> list[ModelT]:
        result = await self.session.execute(select(self.model).limit(limit))
        return list(result.scalars())

    async def update(self, record_id: UUID, **values: object) -> ModelT | None:
        record = await self.get(record_id)
        if record is None:
            return None
        for key, value in values.items():
            if not hasattr(record, key):
                raise ValueError(f"Unknown mutable field: {key}")
            setattr(record, key, value)
        await self.session.flush()
        return record
