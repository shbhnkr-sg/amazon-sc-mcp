FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/amzn/selling-partner-api-models.git /app/sp-api-models

RUN pip install --no-cache-dir "mcp[cli]" httpx uvicorn starlette

COPY *.py .

EXPOSE 8000

CMD ["python", "entrypoint.py"]
