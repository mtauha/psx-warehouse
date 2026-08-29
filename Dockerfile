# ---- builder ----
FROM python:3.11-slim AS builder

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
RUN pip install --no-cache-dir .

# ---- runtime ----
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY extract/ ./extract/
COPY dbt/ ./dbt/

RUN adduser --disabled-password --gecos "" psxuser \
    && chown -R psxuser:psxuser /app

ENV HOME=/home/psxuser
ENV PYTHONPATH=/app

USER psxuser

CMD ["python", "-c", "print('psx-warehouse image placeholder — extraction entrypoint not yet implemented')"]
