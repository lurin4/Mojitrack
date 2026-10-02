FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir uv \
    && uv sync --no-dev \
    && uv run --no-sync python scripts/download_assets.py

RUN useradd --uid 10001 --create-home reader \
    && mkdir -p /app/data /app/backups \
    && chown -R reader:reader /app

USER reader

EXPOSE 8000

CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]