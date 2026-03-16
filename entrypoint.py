"""
Amazon Seller Central MCP Server

Serves official SP-API endpoints as MCP tools via SSE.
Built directly on the MCP Python SDK — no third-party wrappers.
"""

import os
import sys
import json
import httpx
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route, Mount
import uvicorn

from config import get_spec_files
from openapi_loader import load_spec
from sp_auth import SPAPIAuth


def load_all_tools(spec_files: list[str]) -> list[dict]:
    """Load tools from all spec files, skipping broken ones."""
    all_tools = []
    seen_names = set()

    for spec_file in spec_files:
        name = os.path.basename(spec_file)
        try:
            tools = load_spec(spec_file)
            # Deduplicate tool names
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

    # Build a lookup by tool name
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

        # Substitute path parameters
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(
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


def main():
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
        print(f"\nAuth: LWA OAuth configured")
    else:
        print(f"\nWARNING: Missing SP-API credentials — API calls will fail", file=sys.stderr)

    server = create_server(tools, auth)

    print(f"\nTotal: {len(tools)} MCP tools registered")

    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    print(f"\nMCP server on http://{host}:{port}")
    print(f"  SSE: http://{host}:{port}/sse")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
