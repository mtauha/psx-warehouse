# ---- builder ----
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /bin/

WORKDIR /build

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY extract/ ./extract/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---- runtime ----
FROM python:3.11-slim AS runtime

RUN adduser --disabled-password --gecos "" psxuser

WORKDIR /app

COPY --from=builder --chown=psxuser:psxuser /build/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=psxuser:psxuser extract/ ./extract/
COPY --chown=psxuser:psxuser dbt/ ./dbt/

ENV HOME=/home/psxuser
ENV PYTHONPATH=/app

USER psxuser

CMD ["python", "-m", "extract.main"]
