{%- if cookiecutter.enable_teams %}
"""Tests for teams repository layer (organization, member, invitation)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

{%- if cookiecutter.use_postgresql %}


class TestOrganizationRepository:
    """Tests for organization repository (PostgreSQL async)."""

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

    @pytest.mark.anyio
    async def test_get_by_slug_found(self, mock_db):
        from app.repositories import organization as org_repo

        mock_org = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_org
        mock_db.execute.return_value = mock_result

        result = await org_repo.get_by_slug(mock_db, "acme-corp")

        assert result == mock_org

    @pytest.mark.anyio
    async def test_get_by_slug_not_found(self, mock_db):
        from app.repositories import organization as org_repo

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await org_repo.get_by_slug(mock_db, "nonexistent")

        assert result is None

    @pytest.mark.anyio
    async def test_get_personal_for_user(self, mock_db):
        from app.repositories import organization as org_repo

        mock_org = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_org
        mock_db.execute.return_value = mock_result

        result = await org_repo.get_personal_for_user(mock_db, MagicMock())

        assert result == mock_org

    @pytest.mark.anyio
    async def test_create_organization(self, mock_db):
        from app.repositories import organization as org_repo
        import uuid

        created_org = MagicMock()
        created_org.name = "Acme Corp"
        created_org.slug = "acme-corp"

        mock_db.refresh.side_effect = lambda obj: None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.repositories.organization.Organization", return_value=created_org):
            await org_repo.create(
                mock_db,
                name="Acme Corp",
                slug="acme-corp",
                created_by_user_id=uuid.uuid4(),
            )

        mock_db.add.assert_called_once_with(created_org)
        mock_db.flush.assert_called_once()

    @pytest.mark.anyio
    async def test_slugify_basic(self):
        from app.repositories.organization import _slugify

        assert _slugify("Acme Corp") == "acme-corp"
        assert _slugify("  Hello World  ") == "hello-world"
        assert _slugify("Test---Multiple---Dashes") == "test-multiple-dashes"

    @pytest.mark.anyio
    async def test_generate_unique_slug_no_collision(self, mock_db):
        from app.repositories import organization as org_repo

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        slug = await org_repo.generate_unique_slug(mock_db, "Acme Corp")

        assert slug == "acme-corp"

    @pytest.mark.anyio
    async def test_generate_unique_slug_with_collision(self, mock_db):
        from app.repositories import organization as org_repo

        call_count = [0]

        async def mock_execute(*args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            result.scalar.return_value = 1 if call_count[0] == 1 else 0
            return result

        mock_db.execute.side_effect = mock_execute

        slug = await org_repo.generate_unique_slug(mock_db, "Acme Corp")

        assert slug == "acme-corp-2"


class TestMemberRepository:
    """Tests for member repository (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.delete = AsyncMock()
        return db

    @pytest.mark.anyio
    async def test_get_member_found(self, mock_db):
        from app.repositories import member as member_repo
        import uuid

        mock_member = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_member
        mock_db.execute.return_value = mock_result

        result = await member_repo.get(
            mock_db,
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        assert result == mock_member

    @pytest.mark.anyio
    async def test_get_member_not_found(self, mock_db):
        from app.repositories import member as member_repo
        import uuid

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await member_repo.get(
            mock_db,
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        assert result is None

    @pytest.mark.anyio
    async def test_count_for_org(self, mock_db):
        from app.repositories import member as member_repo
        import uuid

        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_db.execute.return_value = mock_result

        count = await member_repo.count_for_org(mock_db, uuid.uuid4())

        assert count == 3

    @pytest.mark.anyio
    async def test_count_billable_excludes_viewer(self, mock_db):
        from app.repositories import member as member_repo
        import uuid

        mock_result = MagicMock()
        mock_result.scalar.return_value = 2
        mock_db.execute.return_value = mock_result

        count = await member_repo.count_billable_for_org(mock_db, uuid.uuid4())

        assert count == 2

    @pytest.mark.anyio
    async def test_create_member(self, mock_db):
        from app.repositories import member as member_repo
        import uuid

        mock_member = MagicMock()
        mock_db.refresh.side_effect = lambda obj: None

        with patch("app.repositories.member.OrganizationMember", return_value=mock_member):
            await member_repo.create(
                mock_db,
                organization_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                role="member",
            )

        mock_db.add.assert_called_once_with(mock_member)
        mock_db.flush.assert_called_once()

    @pytest.mark.anyio
    async def test_update_role(self, mock_db):
        from app.repositories import member as member_repo

        mock_member = MagicMock()
        mock_member.role = "member"

        await member_repo.update_role(mock_db, mock_member, role="admin")

        assert mock_member.role == "admin"
        mock_db.flush.assert_called_once()

    @pytest.mark.anyio
    async def test_delete_member(self, mock_db):
        from app.repositories import member as member_repo

        mock_member = MagicMock()

        await member_repo.delete(mock_db, mock_member)

        mock_db.delete.assert_called_once_with(mock_member)
        mock_db.flush.assert_called_once()


class TestInvitationRepository:
    """Tests for invitation repository (PostgreSQL async)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.get = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.mark.anyio
    async def test_get_by_token_found(self, mock_db):
        from app.repositories import invitation as invitation_repo

        mock_invite = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invite
        mock_db.execute.return_value = mock_result

        result = await invitation_repo.get_by_token(mock_db, "sometoken123")

        assert result == mock_invite

    @pytest.mark.anyio
    async def test_get_by_token_not_found(self, mock_db):
        from app.repositories import invitation as invitation_repo

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await invitation_repo.get_by_token(mock_db, "nonexistent")

        assert result is None

    @pytest.mark.anyio
    async def test_create_invitation_generates_token(self, mock_db):
        from app.repositories import invitation as invitation_repo
        import uuid

        created_invite = None

        def capture_add(obj):
            nonlocal created_invite
            created_invite = obj

        mock_db.add.side_effect = capture_add
        mock_db.refresh.side_effect = lambda obj: None

        await invitation_repo.create(
            mock_db,
            organization_id=uuid.uuid4(),
            email="bob@example.com",
            invited_by_user_id=uuid.uuid4(),
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.anyio
    async def test_create_invitation_lowercases_email(self, mock_db):
        from app.repositories import invitation as invitation_repo
        import uuid

        added_obj = None

        def capture(obj):
            nonlocal added_obj
            added_obj = obj

        mock_db.add.side_effect = capture
        mock_db.refresh.side_effect = lambda obj: None

        await invitation_repo.create(
            mock_db,
            organization_id=uuid.uuid4(),
            email="BOB@EXAMPLE.COM",
            invited_by_user_id=uuid.uuid4(),
        )

        assert added_obj is not None
        assert added_obj.email == "bob@example.com"

    @pytest.mark.anyio
    async def test_accept_invitation(self, mock_db):
        from app.repositories import invitation as invitation_repo
        import uuid

        mock_invite = MagicMock()
        mock_invite.status = "pending"

        await invitation_repo.accept(
            mock_db, mock_invite, accepted_by_user_id=uuid.uuid4()
        )

        assert mock_invite.status == "accepted"
        assert mock_invite.accepted_at is not None
        mock_db.flush.assert_called_once()

    @pytest.mark.anyio
    async def test_revoke_invitation(self, mock_db):
        from app.repositories import invitation as invitation_repo

        mock_invite = MagicMock()
        mock_invite.status = "pending"

        await invitation_repo.revoke(mock_db, mock_invite)

        assert mock_invite.status == "revoked"
        mock_db.flush.assert_called_once()


{%- elif cookiecutter.use_sqlite %}


class TestOrganizationRepository:
    """Tests for organization repository (SQLite sync)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        return db

    def test_get_by_slug_found(self, mock_db):
        from app.repositories import organization as org_repo

        mock_org = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_org
        mock_db.execute.return_value = mock_result

        result = org_repo.get_by_slug(mock_db, "acme-corp")

        assert result == mock_org

    def test_get_by_slug_not_found(self, mock_db):
        from app.repositories import organization as org_repo

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = org_repo.get_by_slug(mock_db, "nonexistent")

        assert result is None

    def test_slugify(self):
        from app.repositories.organization import _slugify

        assert _slugify("Acme Corp") == "acme-corp"
        assert _slugify("  Hello World  ") == "hello-world"

    def test_create_organization(self, mock_db):
        from app.repositories import organization as org_repo

        mock_org = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        with patch("app.repositories.organization.Organization", return_value=mock_org):
            org_repo.create(
                mock_db,
                name="Acme",
                slug="acme",
                created_by_user_id="user-1",
            )

        mock_db.add.assert_called_once_with(mock_org)
        mock_db.flush.assert_called_once()


class TestMemberRepository:
    """Tests for member repository (SQLite sync)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_count_for_org(self, mock_db):
        from app.repositories import member as member_repo

        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result

        count = member_repo.count_for_org(mock_db, "org-1")

        assert count == 5

    def test_update_role(self, mock_db):
        from app.repositories import member as member_repo

        mock_member = MagicMock()
        member_repo.update_role(mock_db, mock_member, role="admin")

        assert mock_member.role == "admin"
        mock_db.flush.assert_called_once()


class TestInvitationRepository:
    """Tests for invitation repository (SQLite sync)."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_get_by_token_not_found(self, mock_db):
        from app.repositories import invitation as invitation_repo

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = invitation_repo.get_by_token(mock_db, "bad-token")

        assert result is None

    def test_create_lowercases_email(self, mock_db):
        from app.repositories import invitation as invitation_repo

        added_obj = None

        def capture(obj):
            nonlocal added_obj
            added_obj = obj

        mock_db.add.side_effect = capture

        invitation_repo.create(
            mock_db,
            organization_id="org-1",
            email="Bob@EXAMPLE.COM",
            invited_by_user_id="user-1",
        )

        assert added_obj is not None
        assert added_obj.email == "bob@example.com"

    def test_accept_sets_status(self, mock_db):
        from app.repositories import invitation as invitation_repo

        mock_invite = MagicMock()
        invitation_repo.accept(mock_db, mock_invite, accepted_by_user_id="user-2")

        assert mock_invite.status == "accepted"


{%- else %}
# Teams tests not applicable for this DB configuration.
{%- endif %}
{%- else %}
"""Teams repository tests — not configured (enable_teams=false)."""
{%- endif %}
