# Backend image for Fly.io. Single-stage on python:3.12-slim — small
# enough for the free tier, plenty fast for the hackathon demo.
#
# Wheels: every runtime dep ships pre-built wheels for linux/amd64
# (asyncpg, pydantic-core, etc.), so no apt-get build-essential needed.

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

# alembic + the migration scripts come along for `fly deploy --release-command`.
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Fly injects PORT (default 8080); fall back to 8000 for `docker run` locally.
EXPOSE 8000

CMD ["sh", "-c", "uvicorn --factory hpao.app:app_factory --host 0.0.0.0 --port ${PORT:-8000}"]
