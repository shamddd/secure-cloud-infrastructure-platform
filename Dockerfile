# syntax=docker/dockerfile:1.7
FROM python:3.12.13-slim-bookworm AS builder

ARG UV_VERSION=0.11.21
ENV UV_CACHE_DIR=/tmp/uv-cache \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
RUN python -m pip install --no-cache-dir "uv==${UV_VERSION}"
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12.13-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="Secure Cloud Infrastructure Platform" \
      org.opencontainers.image.description="Security-first desired-state control plane" \
      org.opencontainers.image.source="https://github.com/shamddd/secure-cloud-infrastructure-platform" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system --gid 10001 scip \
    && useradd --system --uid 10001 --gid scip --home-dir /nonexistent --shell /usr/sbin/nologin scip

WORKDIR /app
COPY --from=builder --chown=scip:scip /app/.venv /app/.venv
COPY --chown=scip:scip alembic.ini ./
COPY --chown=scip:scip migrations ./migrations

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"]

CMD ["uvicorn", "secure_cloud_platform.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=127.0.0.1"]
