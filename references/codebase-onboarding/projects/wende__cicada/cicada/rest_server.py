"""
REST API Server for Cicada MCP Tools.

Exposes all cicada MCP tools as REST endpoints for easy integration
with web applications, scripts, and other services.
"""

from __future__ import annotations

import sys
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cicada import __version__
from cicada.mcp.config_manager import ConfigManager
from cicada.mcp.router import create_tool_router


def format_response(result: str, output_format: str) -> tuple[str | dict, str]:
    """Format MCP tool response based on requested format.

    Args:
        result: The markdown text result from MCP tool
        output_format: Either 'markdown' or 'json'

    Returns:
        Tuple of (formatted_data, format_type)
    """
    if output_format == "json":
        # Return a structured JSON response
        return {
            "content": result,
            "format": "markdown",
            "note": "Content is markdown text. Native JSON format coming in future release.",
        }, "json"
    return result, "markdown"


# Request/Response Models
class QueryRequest(BaseModel):
    query: str | list[str] = Field(..., description="Keywords or patterns to search for")
    scope: str = Field("all", description="Filter scope: all, public, private")
    recent: bool = Field(False, description="Filter to recently changed code")
    result_type: str = Field("all", description="Result type: all, modules, functions")
    match_source: str = Field("all", description="Where to search: all, docs, strings, comments")
    max_results: int = Field(10, description="Maximum results to show")
    offset: int = Field(0, description="Skip first N results")
    glob: str | None = Field(None, description="Glob pattern to filter by file path")
    path: str | None = Field(None, description="Base directory to search in")
    type: str | None = Field(None, description="File type shorthand")
    show_snippets: bool = Field(False, description="Show code snippet previews")
    context_lines: int = Field(2, description="Context lines around definition")
    context_before: int | None = Field(None, description="Lines before definition")
    context_after: int | None = Field(None, description="Lines after definition")
    verbose: bool = Field(False, description="Enable verbose output")
    format: str = Field("markdown", description="Output format: markdown or json")


class SearchModuleRequest(BaseModel):
    module_name: str | None = Field(None, description="Module name or pattern")
    file_path: str | None = Field(None, description="Path to file containing module")
    format: str = Field("markdown", description="Output format: markdown or json")
    type: str = Field("public", description="Which functions to show: public, private, all")
    what_calls_it: bool = Field(False, description="Show where module is used")
    usage_type: str = Field("source", description="Filter usage sites: all, tests, source")
    what_it_calls: bool = Field(False, description="Show module dependencies")
    dependency_depth: int = Field(1, description="Transitive dependency depth")
    show_function_usage: bool = Field(False, description="Show function-level usage details")
    include_docs: bool = Field(False, description="Include function documentation")
    include_specs: bool = Field(False, description="Include type signatures")
    include_moduledoc: bool = Field(False, description="Include module documentation")
    verbose: bool = Field(False, description="Enable verbose output")
    glob: str | None = Field(None, description="Glob pattern to filter results")
    path: str | None = Field(None, description="Base directory to filter results")
    head_limit: int | None = Field(None, description="Maximum results to show")
    offset: int = Field(0, description="Skip first N results")


class SearchFunctionRequest(BaseModel):
    function_name: str = Field(..., description="Function pattern to search")
    module_path: str | None = Field(None, description="Optional module path to filter")
    format: str = Field("markdown", description="Output format: markdown or json")
    include_usage_examples: bool = Field(False, description="Include code snippets")
    max_examples: int = Field(5, description="Maximum number of code examples")
    usage_type: str = Field("source", description="Filter call sites: all, tests, source")
    changed_since: str | None = Field(None, description="Filter by change date")
    what_calls_it: bool = Field(True, description="Show call sites")
    what_it_calls: bool = Field(False, description="Show function dependencies")
    include_code_context: bool = Field(False, description="Include code context for dependencies")
    include_docs: bool = Field(False, description="Include function documentation")
    include_specs: bool = Field(False, description="Include type signatures")
    verbose: bool = Field(False, description="Enable verbose output")
    glob: str | None = Field(None, description="Glob pattern to filter results")
    path: str | None = Field(None, description="Base directory to filter results")
    head_limit: int | None = Field(None, description="Maximum results to show")
    offset: int = Field(0, description="Skip first N results")


class GitHistoryRequest(BaseModel):
    file_path: str = Field(..., description="Path to file")
    start_line: int | None = Field(None, description="Line number or range start")
    end_line: int | None = Field(None, description="Range end")
    function_name: str | None = Field(None, description="Function name for tracking")
    show_evolution: bool = Field(False, description="Show evolution metadata")
    max_results: int = Field(10, description="Maximum commits/PRs to return")
    recent: bool | None = Field(None, description="Time filter: true/false/null")
    recent_days: int | None = Field(None, description="Number of days for recent filter")
    author: str | None = Field(None, description="Filter by author")
    include_pr_description: bool = Field(False, description="Include PR descriptions")
    include_review_comments: bool = Field(False, description="Include PR review comments")
    verbose: bool = Field(False, description="Enable verbose output")
    format: str = Field("markdown", description="Output format: markdown or json")


class ExpandResultRequest(BaseModel):
    identifier: str = Field(..., description="Module or function identifier")
    type: str = Field("auto", description="Type: auto, module, function")
    include_code: bool = Field(True, description="Include code snippets")
    what_calls_it: bool = Field(True, description="Show call sites")
    what_it_calls: bool = Field(False, description="Show dependencies")
    dependency_depth: int = Field(1, description="Transitive dependency depth")
    show_function_usage: bool = Field(False, description="Show function-level usage")
    include_code_context: bool = Field(False, description="Include code context")
    format: str = Field("markdown", description="Output format: markdown or json")


class RefreshIndexRequest(BaseModel):
    force_full: bool = Field(False, description="Force full reindex")
    format: str = Field("markdown", description="Output format: markdown or json")


class QueryJqRequest(BaseModel):
    query: str = Field(..., description="jq query expression")
    format: str = Field("compact", description="Output format: compact or pretty")
    sample: bool = Field(False, description="Auto-limit results to first 5 items")


class ToolResponse(BaseModel):
    success: bool
    data: str | dict[str, Any]
    error: str | None = None
    format: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str


class ToolInfo(BaseModel):
    name: str
    description: str
    endpoint: str


# Create FastAPI app
def create_app(config: dict) -> FastAPI:
    """Create FastAPI application with configured routes."""
    app = FastAPI(
        title="Cicada MCP REST API",
        description="REST API for Cicada MCP tools - code intelligence and search",
        version=__version__,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create tool router
    router, index_manager, git_helper = create_tool_router(config)

    # Health check endpoint
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": __version__}

    # List all available tools
    @app.get("/api/tools", response_model=list[ToolInfo])
    async def list_tools():
        """List all available MCP tools."""
        return [
            {
                "name": "query",
                "description": "Search for code by keywords or patterns",
                "endpoint": "/api/query",
            },
            {
                "name": "search-module",
                "description": "View a module's complete API and dependencies",
                "endpoint": "/api/search-module",
            },
            {
                "name": "search-function",
                "description": "Find function definitions and call sites",
                "endpoint": "/api/search-function",
            },
            {
                "name": "git-history",
                "description": "Get git history for files, lines, or functions",
                "endpoint": "/api/git-history",
            },
            {
                "name": "expand-result",
                "description": "Expand a query result to see complete details",
                "endpoint": "/api/expand-result",
            },
            {
                "name": "refresh-index",
                "description": "Force refresh the code index",
                "endpoint": "/api/refresh-index",
            },
            {
                "name": "query-jq",
                "description": "Execute jq queries against the index",
                "endpoint": "/api/query-jq",
            },
        ]

    # Tool endpoints
    @app.post("/api/query", response_model=ToolResponse)
    async def query_tool(request: QueryRequest):
        """Search for code by keywords or patterns."""
        try:
            result = await router.route_tool("query", request.model_dump(exclude_none=True))
            data, fmt = format_response(result[0].text, request.format)
            return {"success": True, "data": data, "error": None, "format": fmt}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/search-module", response_model=ToolResponse)
    async def search_module_tool(request: SearchModuleRequest):
        """View a module's complete API and dependencies."""
        try:
            result = await router.route_tool("search_module", request.model_dump(exclude_none=True))
            data, fmt = format_response(result[0].text, request.format)
            return {"success": True, "data": data, "error": None, "format": fmt}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/search-function", response_model=ToolResponse)
    async def search_function_tool(request: SearchFunctionRequest):
        """Find function definitions and call sites."""
        try:
            result = await router.route_tool(
                "search_function", request.model_dump(exclude_none=True)
            )
            data, fmt = format_response(result[0].text, request.format)
            return {"success": True, "data": data, "error": None, "format": fmt}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/git-history", response_model=ToolResponse)
    async def git_history_tool(request: GitHistoryRequest):
        """Get git history for files, lines, or functions."""
        try:
            result = await router.route_tool("git_history", request.model_dump(exclude_none=True))
            data, fmt = format_response(result[0].text, request.format)
            return {"success": True, "data": data, "error": None, "format": fmt}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/expand-result", response_model=ToolResponse)
    async def expand_result_tool(request: ExpandResultRequest):
        """Expand a query result to see complete details."""
        try:
            result = await router.route_tool("expand_result", request.model_dump(exclude_none=True))
            data, fmt = format_response(result[0].text, request.format)
            return {"success": True, "data": data, "error": None, "format": fmt}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/refresh-index", response_model=ToolResponse)
    async def refresh_index_tool(request: RefreshIndexRequest):
        """Force refresh the code index."""
        try:

            def refresh_callback(force_full: bool) -> dict:
                return index_manager.force_refresh(force_full=force_full)

            result = await router.route_tool(
                "refresh_index",
                request.model_dump(exclude_none=True),
                refresh_callback=refresh_callback,
            )
            data, fmt = format_response(result[0].text, request.format)
            return {"success": True, "data": data, "error": None, "format": fmt}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/query-jq", response_model=ToolResponse)
    async def query_jq_tool(request: QueryJqRequest):
        """Execute jq queries against the index."""
        try:
            result = await router.route_tool("query_jq", request.model_dump(exclude_none=True))
            # query-jq already returns JSON, so handle it differently
            if request.format == "pretty":
                # The tool respects format parameter natively
                data = result[0].text
                fmt = "json"
            else:
                # Default compact format
                data = result[0].text
                fmt = "json"
            return {"success": True, "data": data, "error": None, "format": fmt}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all uncaught exceptions."""
        return JSONResponse(
            status_code=500,
            content={"success": False, "data": None, "error": str(exc)},
        )

    return app


def run_server(host: str = "0.0.0.0", port: int = 8000, repo_path: str = ".") -> None:
    """Run the REST API server.

    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to listen on (default: 8000)
        repo_path: Path to the repository (default: current directory)
    """
    try:
        import uvicorn
    except ImportError:
        print("Error: FastAPI and uvicorn are required for the REST server.", file=sys.stderr)
        print("Install with: uv pip install fastapi uvicorn", file=sys.stderr)
        sys.exit(1)

    # Load config
    try:
        config_path = ConfigManager.get_config_path()
        config = ConfigManager.load_config(config_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nRun 'cicada install' first to set up the project.", file=sys.stderr)
        sys.exit(1)

    # Create and run app
    app = create_app(config)

    print(f"Starting Cicada REST API server on http://{host}:{port}")
    print(f"API documentation available at http://{host}:{port}/docs")
    print(f"Repository: {config.get('repository', {}).get('path', repo_path)}")
    print("\nPress Ctrl+C to stop the server")

    uvicorn.run(app, host=host, port=port, log_level="info")
