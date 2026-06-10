{%- if cookiecutter.include_example_crud and (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
"""Items routes — example resource scaffold.

Demonstrates the standard route shape:
- Returns ``-> Any`` (response_model handles serialization).
- Uses the ``Annotated`` DI aliases from ``api/deps.py`` — no raw ``Depends()``.
- Per-user ownership via ``CurrentUser``.
- Pagination with ``skip`` / ``limit`` Query params.
"""

from typing import Annotated, Any
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.item import ItemCreate, ItemList, ItemRead, ItemUpdate
from app.services.item import ItemService


router = APIRouter()


def get_item_service(db: DBSession) -> ItemService:
    return ItemService(db)


ItemSvc = Annotated[ItemService, Depends(get_item_service)]


@router.get("", response_model=ItemList)
{%- if cookiecutter.use_postgresql %}
async def list_items(
{%- else %}
def list_items(
{%- endif %}
    service: ItemSvc,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
    """List items owned by the current user."""
{%- if cookiecutter.use_postgresql %}
    items, total = await service.list(owner_id=user.id, skip=skip, limit=limit)
{%- else %}
    items, total = service.list(owner_id=user.id, skip=skip, limit=limit)
{%- endif %}
    return ItemList(items=items, total=total)


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
{%- if cookiecutter.use_postgresql %}
async def create_item(
{%- else %}
def create_item(
{%- endif %}
    data: ItemCreate,
    service: ItemSvc,
    user: CurrentUser,
) -> Any:
    """Create a new item owned by the current user."""
{%- if cookiecutter.use_postgresql %}
    return await service.create(owner_id=user.id, data=data)
{%- else %}
    return service.create(owner_id=user.id, data=data)
{%- endif %}


@router.get("/{item_id}", response_model=ItemRead)
{%- if cookiecutter.use_postgresql %}
async def get_item(
    item_id: UUID,
    service: ItemSvc,
    user: CurrentUser,
) -> Any:
    return await service.get(item_id=item_id, owner_id=user.id)
{%- else %}
def get_item(
    item_id: str,
    service: ItemSvc,
    user: CurrentUser,
) -> Any:
    return service.get(item_id=item_id, owner_id=user.id)
{%- endif %}


@router.patch("/{item_id}", response_model=ItemRead)
{%- if cookiecutter.use_postgresql %}
async def update_item(
    item_id: UUID,
    data: ItemUpdate,
    service: ItemSvc,
    user: CurrentUser,
) -> Any:
    return await service.update(item_id=item_id, owner_id=user.id, data=data)
{%- else %}
def update_item(
    item_id: str,
    data: ItemUpdate,
    service: ItemSvc,
    user: CurrentUser,
) -> Any:
    return service.update(item_id=item_id, owner_id=user.id, data=data)
{%- endif %}


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
{%- if cookiecutter.use_postgresql %}
async def delete_item(
    item_id: UUID,
    service: ItemSvc,
    user: CurrentUser,
) -> None:
    await service.delete(item_id=item_id, owner_id=user.id)
{%- else %}
def delete_item(
    item_id: str,
    service: ItemSvc,
    user: CurrentUser,
) -> None:
    service.delete(item_id=item_id, owner_id=user.id)
{%- endif %}
{%- endif %}
