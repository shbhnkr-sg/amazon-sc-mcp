FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/amzn/selling-partner-api-models.git /app/sp-api-models

RUN pip install --no-cache-dir "mcp[cli]==1.26.0" httpx uvicorn starlette

RUN useradd -m appuser
USER appuser

COPY *.py .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "entrypoint.py"]
