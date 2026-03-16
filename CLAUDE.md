# Amazon Seller Central MCP Server

Docker-based deployment of [mattcoatsworth/AmazonSeller-mcp-server](https://github.com/mattcoatsworth/AmazonSeller-mcp-server) — an MCP server for Amazon's Selling Partner API.

## Stack
- Node.js 20 (Alpine)
- [supergateway](https://www.npmjs.com/package/supergateway) to bridge stdio → SSE (port 3000)
- Docker / Docker Compose

## Files
- `Dockerfile` — builds the MCP server image, installs supergateway
- `docker-compose.yml` — service definition with env_file
- `.env.example` — required SP-API credentials template

## Usage
```bash
cp .env.example .env   # fill in your credentials
docker compose up -d --build
```

## Deployment target
Remote server `mk@192.168.0.150` — pull via git, run docker compose.
