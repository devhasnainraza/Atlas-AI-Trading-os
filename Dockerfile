# Multi-stage production build for Atlas API (Spec 00 FR-041/042).
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /usr/local/bin/uv
WORKDIR /app

# -- Dependency layer: cached unless manifests change -------------------------
FROM base AS deps
COPY pyproject.toml uv.lock ./
COPY shared/pyproject.toml shared/
COPY apps/api/pyproject.toml apps/api/
COPY services/worker/pyproject.toml services/worker/
COPY services/scheduler/pyproject.toml services/scheduler/
RUN uv sync --frozen --no-install-workspace

# -- Production target: non-root, dynamic PORT support ------------------------
FROM deps AS prod
COPY shared/ shared/
COPY apps/api/ apps/api/
RUN uv sync --frozen --no-dev \
    && groupadd --system atlas \
    && useradd --system --gid atlas --no-create-home atlas \
    && chown -R atlas:atlas /app
USER atlas
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys,os; port=os.getenv('PORT','8000'); sys.exit(0 if urllib.request.urlopen(f'http://localhost:{port}/v1/health/live').status==200 else 1)"
CMD ["sh", "-c", "uv run --no-dev uvicorn atlas_api.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
