{%- if cookiecutter.include_example_crud and (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
"""Item service — example resource scaffold.

Wraps `item_repo` with business logic + ownership checks. Routes call THIS,
never the repo directly. Domain exceptions (`NotFoundError`,
`AuthorizationError`) get auto-mapped to HTTP responses by the global
exception handler.
"""

{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

{%- if cookiecutter.use_postgresql %}
from sqlalchemy.ext.asyncio import AsyncSession
{%- else %}
from sqlalchemy.orm import Session
{%- endif %}

from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.models.item import Item
from app.repositories import item as item_repo
from app.schemas.item import ItemCreate, ItemUpdate


class ItemService:
{%- if cookiecutter.use_postgresql %}
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, *, item_id: UUID, owner_id: UUID) -> Item:
        item = await item_repo.get_by_id(self.db, item_id)
        if not item:
            raise NotFoundError(message="Item not found", details={"item_id": str(item_id)})
        if item.owner_id != owner_id:
            # Don't leak existence to non-owners — same 404 as missing.
            raise NotFoundError(message="Item not found", details={"item_id": str(item_id)})
        return item

    async def list(
        self, *, owner_id: UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[Item], int]:
        return await item_repo.list_for_owner(
            self.db, owner_id=owner_id, skip=skip, limit=limit
        )

    async def create(self, *, owner_id: UUID, data: ItemCreate) -> Item:
        return await item_repo.create(
            self.db,
            owner_id=owner_id,
            name=data.name,
            description=data.description,
            is_published=data.is_published,
        )

    async def update(
        self, *, item_id: UUID, owner_id: UUID, data: ItemUpdate
    ) -> Item:
        item = await self.get(item_id=item_id, owner_id=owner_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return item
        return await item_repo.update(self.db, db_item=item, update_data=update_data)

    async def delete(self, *, item_id: UUID, owner_id: UUID) -> None:
        # Resolve through `.get()` so the ownership check runs.
        await self.get(item_id=item_id, owner_id=owner_id)
        await item_repo.delete(self.db, item_id)
{%- else %}
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, *, item_id: str, owner_id: str) -> Item:
        item = item_repo.get_by_id(self.db, item_id)
        if not item or item.owner_id != owner_id:
            raise NotFoundError(message="Item not found", details={"item_id": item_id})
        return item

    def list(
        self, *, owner_id: str, skip: int = 0, limit: int = 50
    ) -> tuple[list[Item], int]:
        return item_repo.list_for_owner(self.db, owner_id=owner_id, skip=skip, limit=limit)

    def create(self, *, owner_id: str, data: ItemCreate) -> Item:
        return item_repo.create(
            self.db,
            owner_id=owner_id,
            name=data.name,
            description=data.description,
            is_published=data.is_published,
        )

    def update(self, *, item_id: str, owner_id: str, data: ItemUpdate) -> Item:
        item = self.get(item_id=item_id, owner_id=owner_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return item
        return item_repo.update(self.db, db_item=item, update_data=update_data)

    def delete(self, *, item_id: str, owner_id: str) -> None:
        self.get(item_id=item_id, owner_id=owner_id)
        item_repo.delete(self.db, item_id)
{%- endif %}
{%- endif %}
