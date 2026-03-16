# Amazon Seller Central MCP Server

MCP server built from official [Amazon SP-API OpenAPI specs](https://github.com/amzn/selling-partner-api-models) using [openapi2mcp](https://pypi.org/project/openapi2mcp/).

## Stack
- Python 3.14 / openapi2mcp / uvicorn
- Docker / Docker Compose
- SSE transport on port 8000 (mapped to host 3100)

## Files
- `entrypoint.py` — loads specs, configures auth, starts MCP server
- `config.py` — model selection logic (core defaults, env-configurable)
- `Dockerfile` — builds image with SP-API models + openapi2mcp
- `docker-compose.yml` — service definition
- `.env.example` — required credentials template

## Usage
```bash
cp .env.example .env   # fill in SP-API credentials
docker compose up -d --build
```

## Model selection
- Default: 12 core seller APIs (orders, catalog, listings, inventory, etc.)
- Set `SP_API_MODELS=all` for all 51 APIs
- Or comma-separate specific model names

## Deployment
Remote server `mk@192.168.0.150` — pull via git, run docker compose.
