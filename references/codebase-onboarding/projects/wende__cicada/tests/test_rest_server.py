"""
Tests for REST API server functionality.

Tests cover:
- REST server creation and configuration
- API endpoint routing
- Error handling
- FastAPI integration
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from cicada.commands import get_argument_parser, handle_command
from cicada.rest_server import create_app


@pytest.fixture
def mock_config():
    """Mock config for REST server tests."""
    return {
        "repository": {"path": str(Path.cwd())},
        "keyword_extraction": {"method": "regular"},
        "keyword_expansion": {"method": "lemmi"},
    }


@pytest.fixture
def mock_router():
    """Mock tool router for REST server tests."""
    with patch("cicada.rest_server.create_tool_router") as mock_create:
        mock_tool_router = MagicMock()
        mock_index_manager = MagicMock()
        mock_git_helper = MagicMock()

        mock_create.return_value = (mock_tool_router, mock_index_manager, mock_git_helper)

        # Setup async route_tool method
        async def async_route_tool(*args, **kwargs):
            from mcp.types import TextContent

            return [TextContent(type="text", text="Mock response")]

        mock_tool_router.route_tool = AsyncMock(side_effect=async_route_tool)

        yield mock_tool_router


@pytest.fixture
def test_client(mock_config, mock_router):
    """Create a test client for the REST API."""
    app = create_app(mock_config)
    return TestClient(app)


class TestRESTServerCLI:
    """Test REST server CLI integration."""

    def test_serve_subcommand_exists(self):
        """Test that serve subcommand is registered."""
        parser = get_argument_parser()
        args = parser.parse_args(["serve"])
        assert args.command == "serve"

    def test_serve_with_default_args(self):
        """Test serve command with default arguments."""
        parser = get_argument_parser()
        args = parser.parse_args(["serve"])
        assert args.command == "serve"
        assert args.repo == "."
        assert args.host == "0.0.0.0"
        assert args.port == 8000

    def test_serve_with_custom_port(self):
        """Test serve command with custom port."""
        parser = get_argument_parser()
        args = parser.parse_args(["serve", "--port", "3000"])
        assert args.port == 3000

    def test_serve_with_custom_host(self):
        """Test serve command with custom host."""
        parser = get_argument_parser()
        args = parser.parse_args(["serve", "--host", "127.0.0.1"])
        assert args.host == "127.0.0.1"

    def test_serve_with_repo_path(self):
        """Test serve command with custom repository path."""
        parser = get_argument_parser()
        args = parser.parse_args(["serve", "/path/to/repo"])
        assert args.repo == "/path/to/repo"

    @patch("cicada.rest_server.run_server")
    def test_handle_serve_command(self, mock_run_server):
        """Test that handle_command routes to handle_serve."""
        parser = get_argument_parser()
        args = parser.parse_args(["serve"])

        result = handle_command(args)
        assert result is True
        mock_run_server.assert_called_once()


class TestRESTServerApp:
    """Test REST server application."""

    def test_app_creation(self, mock_config, mock_router):
        """Test that FastAPI app is created successfully."""
        app = create_app(mock_config)
        assert app is not None
        assert app.title == "Cicada MCP REST API"

    def test_health_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_list_tools_endpoint(self, test_client):
        """Test list tools endpoint."""
        response = test_client.get("/api/tools")
        assert response.status_code == 200
        tools = response.json()
        assert isinstance(tools, list)
        assert len(tools) == 7  # 7 MCP tools

        # Check that all expected tools are present
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "query",
            "search-module",
            "search-function",
            "git-history",
            "expand-result",
            "refresh-index",
            "query-jq",
        ]
        assert all(name in tool_names for name in expected_tools)

    def test_query_endpoint(self, test_client, mock_router):
        """Test query API endpoint."""
        response = test_client.post(
            "/api/query", json={"query": "authentication", "max_results": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["error"] is None
        assert data["format"] == "markdown"

    def test_query_endpoint_json_format(self, test_client, mock_router):
        """Test query API endpoint with JSON format."""
        response = test_client.post(
            "/api/query", json={"query": "authentication", "format": "json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], dict)
        assert "content" in data["data"]
        assert data["format"] == "json"

    def test_search_module_endpoint(self, test_client, mock_router):
        """Test search-module API endpoint."""
        response = test_client.post("/api/search-module", json={"module_name": "MyApp.User"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_search_function_endpoint(self, test_client, mock_router):
        """Test search-function API endpoint."""
        response = test_client.post("/api/search-function", json={"function_name": "create_user"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_git_history_endpoint(self, test_client, mock_router):
        """Test git-history API endpoint."""
        response = test_client.post("/api/git-history", json={"file_path": "lib/auth.ex"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_git_history_endpoint_json_format(self, test_client, mock_router):
        """Test git-history API endpoint with JSON format."""
        response = test_client.post(
            "/api/git-history", json={"file_path": "lib/auth.ex", "format": "json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], dict)
        assert "content" in data["data"]
        assert data["format"] == "json"

    def test_expand_result_endpoint(self, test_client, mock_router):
        """Test expand-result API endpoint."""
        response = test_client.post("/api/expand-result", json={"identifier": "MyApp.Auth"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_refresh_index_endpoint(self, test_client, mock_router):
        """Test refresh-index API endpoint."""
        response = test_client.post("/api/refresh-index", json={"force_full": False})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_query_jq_endpoint(self, test_client, mock_router):
        """Test query-jq API endpoint."""
        response = test_client.post("/api/query-jq", json={"query": ".modules | keys"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_cors_configured(self, mock_config, mock_router):
        """Test that CORS middleware is configured in the app."""
        # Create app and verify middleware is present
        app = create_app(mock_config)

        # Check that middleware is configured (CORS is added via add_middleware)
        assert len(app.user_middleware) > 0

    def test_invalid_endpoint(self, test_client):
        """Test that invalid endpoints return 404."""
        response = test_client.get("/api/invalid")
        assert response.status_code == 404


class TestRESTServerErrors:
    """Test REST server error handling."""

    def test_query_validation_error(self, test_client):
        """Test query endpoint with missing required field."""
        response = test_client.post("/api/query", json={})
        assert response.status_code == 422  # Validation error

    def test_search_function_validation_error(self, test_client):
        """Test search-function endpoint with missing required field."""
        response = test_client.post("/api/search-function", json={})
        assert response.status_code == 422  # Validation error

    def test_git_history_validation_error(self, test_client):
        """Test git-history endpoint with missing required field."""
        response = test_client.post("/api/git-history", json={})
        assert response.status_code == 422  # Validation error

    @patch("cicada.rest_server.run_server")
    def test_serve_keyboard_interrupt(self, mock_run_server):
        """Test that serve handles keyboard interrupt gracefully."""
        from cicada.commands import handle_serve

        mock_run_server.side_effect = KeyboardInterrupt()

        parser = get_argument_parser()
        args = parser.parse_args(["serve"])

        with pytest.raises(SystemExit) as exc_info:
            handle_serve(args)

        assert exc_info.value.code == 0

    @patch("cicada.rest_server.run_server")
    def test_serve_error_handling(self, mock_run_server):
        """Test that serve handles errors properly."""
        from cicada.commands import handle_serve

        mock_run_server.side_effect = RuntimeError("Server error")

        parser = get_argument_parser()
        args = parser.parse_args(["serve"])

        with pytest.raises(SystemExit) as exc_info:
            handle_serve(args)

        assert exc_info.value.code == 1
