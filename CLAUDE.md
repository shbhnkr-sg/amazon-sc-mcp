# Amazon Seller Central MCP Server

MCP server built directly on the [MCP Python SDK](https://pypi.org/project/mcp/) from official [Amazon SP-API Swagger specs](https://github.com/amzn/selling-partner-api-models).

## Stack
- Python 3.14 / mcp SDK / httpx / uvicorn / starlette
- Docker / Docker Compose
- SSE transport on port 8000 (mapped to host 3100)

## Files
- `entrypoint.py` — MCP server with SSE transport, tool dispatch, API calls
- `openapi_loader.py` — parses Swagger 2.0 specs into MCP tool definitions
- `sp_auth.py` — LWA OAuth refresh_token flow for SP-API auth
- `config.py` — model selection logic (core defaults, env-configurable)
- `Dockerfile` — builds image with SP-API models + MCP SDK
- `docker-compose.yml` — service definition
- `.env.example` — required SP-API credentials template

## Usage
```bash
cp .env.example .env   # fill in SP-API credentials
docker compose up -d --build
```

## Model selection
- Default: 12 core seller APIs
- Set `SP_API_MODELS=all` for all 51 APIs
- Or comma-separate specific model names

## Deployment
Remote server `mk@192.168.0.150` — pull via git, run docker compose.
