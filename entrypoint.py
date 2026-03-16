"""
Amazon Seller Central MCP Server

Loads official SP-API OpenAPI specs and serves them as MCP tools via SSE.
Specs with circular $ref or parse errors are skipped gracefully.
"""

import os
import sys
import json
import uvicorn
from config import get_spec_files


def load_specs_resilient(spec_files, auth_config):
    """Load specs one by one, skipping any that fail to parse."""
    from openapi2mcp.server import MCPServer

    valid_specs = []
    for spec_file in spec_files:
        name = os.path.basename(spec_file)
        try:
            # Test-load: create a throwaway server with just this spec
            test = MCPServer(spec_files=[spec_file], auth_config=auth_config)
            if test.tools:
                valid_specs.append(spec_file)
                print(f"  OK  {name} ({len(test.tools)} tools)")
            else:
                print(f"  SKIP {name} (0 tools extracted)")
        except Exception as e:
            err_msg = str(e).split("\n")[0][:120]
            print(f"  FAIL {name}: {err_msg}")

    if not valid_specs:
        print("ERROR: No specs loaded successfully.", file=sys.stderr)
        sys.exit(1)

    # Build final server with all valid specs
    server = MCPServer(spec_files=valid_specs, auth_config=auth_config)
    return server


def main():
    spec_files = get_spec_files()

    if not spec_files:
        print("ERROR: No SP-API spec files found. Check SP_API_MODELS env var.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {len(spec_files)} SP-API specs:\n")

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
        print("Auth: LWA OAuth configured\n")
    else:
        print("WARNING: No SP-API credentials set - API calls will fail auth\n", file=sys.stderr)

    server = load_specs_resilient(spec_files, auth_config)

    print(f"\nTotal: {len(server.tools)} MCP tools registered")

    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    print(f"\nMCP server listening on http://{host}:{port}")
    print(f"  SSE endpoint:  http://{host}:{port}/sse")

    app = server.get_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
