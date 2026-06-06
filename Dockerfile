# Backend image for Railway. Single-stage on python:3.12-slim.
#
# Wheels: every runtime dep ships pre-built wheels for linux/amd64
# (asyncpg, pydantic-core), so no apt-get build-essential needed.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy only the files pip needs to resolve dependencies first so the
# layer caches even when src/ changes.
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --upgrade pip \
 && pip install .

COPY alembic.ini ./
COPY alembic/ ./alembic/

EXPOSE 8000

CMD ["sh", "-c", "uvicorn --factory lizzie.app:app_factory --host 0.0.0.0 --port ${PORT:-8000}"]
