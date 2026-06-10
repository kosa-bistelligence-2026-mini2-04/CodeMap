{%- if cookiecutter.enable_teams %}
"""Tests for OrganizationService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

{%- if cookiecutter.use_postgresql %}


class TestOrganizationService:
    """Tests for OrganizationService (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.get = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        from app.services.organization import OrganizationService
        return OrganizationService(mock_db)

    @pytest.mark.anyio
    async def test_create_generates_slug_when_absent(self, service, mock_db):
        import uuid
        from app.schemas.organization import OrganizationCreate

        mock_org = MagicMock()
        mock_org.id = uuid.uuid4()
        mock_member = MagicMock()

        with (
            patch("app.services.organization.organization_repo.slug_exists", new=AsyncMock(return_value=False)),
            patch("app.services.organization.organization_repo.generate_unique_slug", new=AsyncMock(return_value="my-org")),
            patch("app.services.organization.organization_repo.create", new=AsyncMock(return_value=mock_org)),
            patch("app.services.organization.member_repo.create", new=AsyncMock(return_value=mock_member)),
        ):
            result = await service.create(
                OrganizationCreate(name="My Org"),
                owner_id=uuid.uuid4(),
            )

        assert result == mock_org

    @pytest.mark.anyio
    async def test_create_raises_if_slug_taken(self, service, mock_db):
        import uuid
        from app.core.exceptions import AlreadyExistsError
        from app.schemas.organization import OrganizationCreate

        with (
            patch("app.services.organization.organization_repo.slug_exists", new=AsyncMock(return_value=True)),
            pytest.raises(AlreadyExistsError),
        ):
            await service.create(
                OrganizationCreate(name="Taken", slug="taken-slug"),
                owner_id=uuid.uuid4(),
            )

    @pytest.mark.anyio
    async def test_create_personal_org(self, service, mock_db):
        import uuid
        mock_org = MagicMock()
        mock_org.id = uuid.uuid4()

        with (
            patch("app.services.organization.organization_repo.generate_unique_slug", new=AsyncMock(return_value="alice")),
            patch("app.services.organization.organization_repo.create", new=AsyncMock(return_value=mock_org)),
            patch("app.services.organization.member_repo.create", new=AsyncMock()),
        ):
            result = await service.create_personal_org(uuid.uuid4(), "alice@example.com")

        assert result == mock_org

    @pytest.mark.anyio
    async def test_delete_blocks_personal_org(self, service, mock_db):
        import uuid
        from app.core.exceptions import BadRequestError

        mock_org = MagicMock()
        mock_org.is_personal = True
        mock_membership = MagicMock()
        mock_membership.role = "owner"

        with (
            patch.object(service, "get_for_user", new=AsyncMock(return_value=(mock_org, mock_membership))),
            pytest.raises(BadRequestError),
        ):
            await service.delete(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.anyio
    async def test_delete_blocks_non_owner(self, service, mock_db):
        import uuid
        from app.core.exceptions import AuthorizationError

        mock_org = MagicMock()
        mock_org.is_personal = False
        mock_membership = MagicMock()
        mock_membership.role = "admin"

        with (
            patch.object(service, "get_for_user", new=AsyncMock(return_value=(mock_org, mock_membership))),
            pytest.raises(AuthorizationError),
        ):
            await service.delete(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.anyio
    async def test_delete_succeeds_for_owner(self, service, mock_db):
        import uuid
        mock_org = MagicMock()
        mock_org.is_personal = False
        mock_membership = MagicMock()
        mock_membership.role = "owner"

        with (
            patch.object(service, "get_for_user", new=AsyncMock(return_value=(mock_org, mock_membership))),
            patch("app.services.organization.organization_repo.delete", new=AsyncMock()),
        ):
            await service.delete(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.anyio
    async def test_update_requires_admin_or_owner(self, service, mock_db):
        import uuid
        from app.core.exceptions import AuthorizationError
        from app.schemas.organization import OrganizationUpdate

        mock_org = MagicMock()
        mock_membership = MagicMock()
        mock_membership.role = "member"

        with (
            patch.object(service, "get_for_user", new=AsyncMock(return_value=(mock_org, mock_membership))),
            pytest.raises(AuthorizationError),
        ):
            await service.update(uuid.uuid4(), OrganizationUpdate(name="New"), requester_id=uuid.uuid4())

    @pytest.mark.anyio
    async def test_get_for_user_raises_if_not_member(self, service, mock_db):
        import uuid
        from app.core.exceptions import NotFoundError

        with (
            patch("app.services.organization.member_repo.get", new=AsyncMock(return_value=None)),
            pytest.raises(NotFoundError),
        ):
            await service.get_for_user(uuid.uuid4(), uuid.uuid4())


class TestUserServiceRegistrationWithOrg:
    """Tests that UserService.register creates a Personal Org."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.mark.anyio
    async def test_register_creates_personal_org(self, mock_db):
        from app.services.user import UserService
        from app.schemas.user import UserCreate

        mock_user = MagicMock()
        mock_user.id = MagicMock()

        with (
            patch("app.services.user.user_repo.get_by_email", new=AsyncMock(return_value=None)),
            patch("app.services.user.user_repo.create", new=AsyncMock(return_value=mock_user)),
            patch("app.services.user.OrganizationService.create_personal_org", new=AsyncMock()) as mock_create_org,
        ):
            svc = UserService(mock_db)
            await svc.register(UserCreate(email="new@example.com", password="password123"))

        mock_create_org.assert_called_once()


{%- elif cookiecutter.use_sqlite %}


class TestOrganizationService:
    """Tests for OrganizationService (SQLite sync)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        from app.services.organization import OrganizationService
        return OrganizationService(mock_db)

    def test_create_raises_if_slug_taken(self, service):
        from app.core.exceptions import AlreadyExistsError
        from app.schemas.organization import OrganizationCreate

        with (
            patch("app.services.organization.organization_repo.slug_exists", return_value=True),
            pytest.raises(AlreadyExistsError),
        ):
            service.create(OrganizationCreate(name="Taken", slug="taken-slug"), owner_id="user-1")

    def test_delete_blocks_personal_org(self, service):
        from app.core.exceptions import BadRequestError

        mock_org = MagicMock()
        mock_org.is_personal = True
        mock_membership = MagicMock()
        mock_membership.role = "owner"

        with (
            patch.object(service, "get_for_user", return_value=(mock_org, mock_membership)),
            pytest.raises(BadRequestError),
        ):
            service.delete("org-1", "user-1")

    def test_delete_blocks_non_owner(self, service):
        from app.core.exceptions import AuthorizationError

        mock_org = MagicMock()
        mock_org.is_personal = False
        mock_membership = MagicMock()
        mock_membership.role = "admin"

        with (
            patch.object(service, "get_for_user", return_value=(mock_org, mock_membership)),
            pytest.raises(AuthorizationError),
        ):
            service.delete("org-1", "user-1")

    def test_update_requires_admin_or_owner(self, service):
        from app.core.exceptions import AuthorizationError
        from app.schemas.organization import OrganizationUpdate

        mock_org = MagicMock()
        mock_membership = MagicMock()
        mock_membership.role = "member"

        with (
            patch.object(service, "get_for_user", return_value=(mock_org, mock_membership)),
            pytest.raises(AuthorizationError),
        ):
            service.update("org-1", OrganizationUpdate(name="New"), requester_id="user-1")


{%- else %}
# Service tests not applicable for this DB configuration.
{%- endif %}
{%- else %}
"""Organization service tests — not configured (enable_teams=false)."""
{%- endif %}
