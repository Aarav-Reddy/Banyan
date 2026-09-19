FROM ghcr.io/astral-sh/uv:0.12.17 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY apps/api ./apps/api
COPY data ./data
COPY scripts/reset_demo.py ./scripts/reset_demo.py
RUN useradd --create-home --uid 10001 philanthra && mkdir -p /app/.runtime && chown -R philanthra:philanthra /app/.runtime
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH="/app/apps/api" PYTHONDONTWRITEBYTECODE=1
USER philanthra
WORKDIR /app/apps/api
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "45", "--access-logfile", "/dev/null", "--no-control-socket"]
