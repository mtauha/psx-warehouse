# ---- builder ----
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /bin/

WORKDIR /build

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev --extra dbt

COPY extract/ ./extract/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra dbt

ENV PATH="/build/.venv/bin:$PATH"
COPY dbt/ ./dbt/
RUN dbt deps --project-dir dbt

# ---- runtime ----
FROM python:3.11-slim AS runtime

RUN adduser --disabled-password --gecos "" psxuser

WORKDIR /app

COPY --from=builder --chown=psxuser:psxuser /build/.venv /app/.venv
RUN sed -i 's|#!/build/.venv/bin/python|#!/app/.venv/bin/python|g' /app/.venv/bin/*
ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=psxuser:psxuser extract/ ./extract/
COPY --from=builder --chown=psxuser:psxuser /build/dbt ./dbt/
COPY --chown=psxuser:psxuser entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENV HOME=/home/psxuser
ENV PYTHONPATH=/app

USER psxuser

CMD ["./entrypoint.sh"]
