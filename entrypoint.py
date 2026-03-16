"""
Amazon Seller Central MCP Server

Loads official SP-API OpenAPI specs and serves them as MCP tools via SSE.
"""

import os
import sys
import uvicorn
from config import get_spec_files

def main():
    spec_files = get_spec_files()

    if not spec_files:
        print("ERROR: No SP-API spec files found. Check SP_API_MODELS env var.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {len(spec_files)} SP-API specs:")
    for f in spec_files:
        print(f"  - {os.path.basename(f)}")

    auth_config = None
    client_id = os.environ.get("SP_API_CLIENT_ID")
    client_secret = os.environ.get("SP_API_CLIENT_SECRET")
    token_url = os.environ.get("SP_API_TOKEN_URL", "https://api.amazon.com/auth/o2/token")

    if client_id and client_secret:
        auth_config = {
            "client_id": client_id,
            "client_secret": client_secret,
            "token_url": token_url,
        }
        print("Auth configured (LWA OAuth)")
    else:
        print("WARNING: No SP-API credentials set - API calls will fail auth", file=sys.stderr)

    from openapi2mcp.server import MCPServer

    server = MCPServer(
        spec_files=spec_files,
        auth_config=auth_config,
    )

    print(f"\nRegistered {len(server.tools)} MCP tools")

    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    print(f"\nMCP server listening on http://{host}:{port}")
    print(f"  SSE endpoint:  http://{host}:{port}/sse")

    app = server.get_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
