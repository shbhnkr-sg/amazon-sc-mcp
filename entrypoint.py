"""
Amazon Seller Central MCP Server

Serves official SP-API endpoints as MCP tools via Streamable HTTP.
Built on the MCP Python SDK low-level Server for exact schema fidelity.
"""

import os
import sys
import json
import contextlib
import httpx
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse
import uvicorn

from config import get_spec_files
from openapi_loader import load_spec
from sp_auth import SPAPIAuth

# Shared HTTP client — created at startup, closed on shutdown
_http_client: httpx.AsyncClient | None = None


def load_all_tools(spec_files: list[str]) -> list[dict]:
    """Load tools from all spec files, skipping broken ones."""
    all_tools = []
    seen_names = set()

    for spec_file in spec_files:
        name = os.path.basename(spec_file)
        try:
            tools = load_spec(spec_file)
            new_tools = []
            for t in tools:
                if t["name"] not in seen_names:
                    seen_names.add(t["name"])
                    new_tools.append(t)
            all_tools.extend(new_tools)
            print(f"  OK  {name} ({len(new_tools)} tools)")
        except Exception as e:
            err = str(e).split("\n")[0][:120]
            print(f"  FAIL {name}: {err}")

    return all_tools


def create_server(tools: list[dict], auth: SPAPIAuth) -> Server:
    """Create an MCP Server with tools for each SP-API endpoint."""
    server = Server("amazon-seller-central")
    tool_map = {t["name"]: t for t in tools}

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in tools
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        tool_def = tool_map.get(name)
        if not tool_def:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        method = tool_def["method"]
        path = tool_def["path"]
        base_url = tool_def["base_url"]

        query_params = {}
        body = None
        headers = await auth.auth_headers()
        headers["Content-Type"] = "application/json"

        for param_name, value in arguments.items():
            placeholder = f"{{{param_name}}}"
            if placeholder in path:
                path = path.replace(placeholder, str(value))
            elif param_name == "body":
                try:
                    body = json.loads(value) if isinstance(value, str) else value
                except json.JSONDecodeError:
                    body = value
            else:
                query_params[param_name] = value

        url = f"{base_url}{path}"

        try:
            assert _http_client is not None
            resp = await _http_client.request(
                method=method,
                url=url,
                params=query_params or None,
                json=body,
                headers=headers,
            )
            result = {
                "status": resp.status_code,
                "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            }
        except Exception as e:
            result = {"error": str(e)}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return server


async def health(request):
    return JSONResponse({"status": "ok"})


def main():
    global _http_client

    spec_files = get_spec_files()
    if not spec_files:
        print("ERROR: No SP-API spec files found.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {len(spec_files)} SP-API specs:\n")
    tools = load_all_tools(spec_files)
    if not tools:
        print("ERROR: No tools loaded.", file=sys.stderr)
        sys.exit(1)

    auth = SPAPIAuth()
    if auth.configured:
        print("\nAuth: LWA OAuth configured")
    else:
        print("\nWARNING: Missing SP-API credentials — API calls will fail", file=sys.stderr)

    server = create_server(tools, auth)
    print(f"\nTotal: {len(tools)} MCP tools registered")

    session_manager = StreamableHTTPSessionManager(
        app=server,
        stateless=True,
        json_response=True,
    )

    @contextlib.asynccontextmanager
    async def lifespan(app):
        global _http_client
        _http_client = httpx.AsyncClient(timeout=30.0)
        async with session_manager.run():
            yield
        await _http_client.aclose()
        _http_client = None

    async def handle_mcp(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)

    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    app = Starlette(
        routes=[
            Route("/health", health),
            Mount("/mcp", app=handle_mcp),
        ],
        lifespan=lifespan,
    )

    print(f"\nMCP server on http://{host}:{port}")
    print(f"  Streamable HTTP: http://{host}:{port}/mcp")
    print(f"  Health: http://{host}:{port}/health")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
