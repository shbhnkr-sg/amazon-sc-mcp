# Amazon Seller Central MCP Server

MCP server built on the [MCP Python SDK](https://pypi.org/project/mcp/) (low-level Server) from official [Amazon SP-API Swagger specs](https://github.com/amzn/selling-partner-api-models).

## Stack
- Python 3.14 / mcp==1.26.0 / httpx / uvicorn / starlette
- Streamable HTTP transport (single /mcp endpoint)
- Docker / Docker Compose

## Files
- `entrypoint.py` — MCP server: tool registration, dispatch, Streamable HTTP transport
- `openapi_loader.py` — parses Swagger 2.0 specs into MCP tool definitions with exact JSON Schema
- `sp_auth.py` — LWA OAuth refresh_token flow for SP-API auth
- `config.py` — model selection logic (12 core APIs by default, configurable via SP_API_MODELS)
- `test_server.py` — end-to-end MCP protocol smoke test (works without credentials)

## Usage
```bash
cp .env.example .env   # fill in SP-API credentials
docker compose up -d --build
```

## Testing
```bash
# Inside container
python test_server.py http://localhost:8000

# Remote
python test_server.py http://192.168.0.150:3100
```

## Model selection
- Default: 12 core seller APIs
- `SP_API_MODELS=all` for all 51 APIs
- Or comma-separate specific model directory names

## Endpoints
- `POST /mcp` — MCP Streamable HTTP (main protocol endpoint)
- `GET /health` — healthcheck (returns `{"status": "ok"}`)

## Security
- Origin header validation via `MCP_ALLOWED_ORIGINS` env var
- Set to comma-separated allowed origins (empty = allow all)

## Error Handling
- Unknown tools → JSON-RPC error (McpError, never reaches LLM)
- API failures → structured JSON response (LLM sees and can retry)
- Auth failures → graceful error message (server stays running)

## Tool Annotations
- GET endpoints → `readOnlyHint: true`
- DELETE endpoints → `destructiveHint: true`
- PUT endpoints → `idempotentHint: true`
- All endpoints → `openWorldHint: true` (external SP-API calls)
