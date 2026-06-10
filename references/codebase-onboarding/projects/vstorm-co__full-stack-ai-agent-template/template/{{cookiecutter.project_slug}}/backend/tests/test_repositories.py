{%- if cookiecutter.use_jwt %}
"""Tests for repository layer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

{%- if cookiecutter.use_postgresql %}


class TestUserRepository:
    """Tests for user repository functions."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.anyio
    async def test_get_by_email(self, mock_session):
        """Test get_by_email returns user."""
        from app.repositories import user as user_repo

        mock_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await user_repo.get_by_email(mock_session, "test@example.com")

        assert result == mock_user

    @pytest.mark.anyio
    async def test_get_by_email_not_found(self, mock_session):
        """Test get_by_email returns None when not found."""
        from app.repositories import user as user_repo

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await user_repo.get_by_email(mock_session, "notfound@example.com")

        assert result is None
{%- elif cookiecutter.use_sqlite %}


class TestUserRepository:
    """Tests for user repository functions."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock sync session."""
        session = MagicMock()
        return session

    def test_get_by_email(self, mock_session):
        """Test get_by_email returns user."""
        from app.repositories import user as user_repo

        mock_user = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = user_repo.get_by_email(mock_session, "test@example.com")

        assert result == mock_user

    def test_get_by_email_not_found(self, mock_session):
        """Test get_by_email returns None when not found."""
        from app.repositories import user as user_repo

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = user_repo.get_by_email(mock_session, "notfound@example.com")

        assert result is None
{%- elif cookiecutter.use_mongodb %}


class TestUserRepository:
    """Tests for user repository functions."""

    @pytest.mark.anyio
    async def test_get_by_email(self):
        """Test get_by_email returns user."""
        from app.repositories import user as user_repo

        mock_user = MagicMock()

        with patch("app.repositories.user.User") as MockUser:
            MockUser.find_one = AsyncMock(return_value=mock_user)

            result = await user_repo.get_by_email("test@example.com")

            assert result == mock_user

    @pytest.mark.anyio
    async def test_get_by_email_not_found(self):
        """Test get_by_email returns None when not found."""
        from app.repositories import user as user_repo

        with patch("app.repositories.user.User") as MockUser:
            MockUser.find_one = AsyncMock(return_value=None)

            result = await user_repo.get_by_email("notfound@example.com")

            assert result is None
{%- endif %}
{%- endif %}
