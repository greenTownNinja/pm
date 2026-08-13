FROM node:26-bookworm-slim AS frontend

WORKDIR /frontend

# Lockfile first so edits to the source do not invalidate the install layer.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# Fonts are vendored, so this needs no network access.
RUN npm run build


FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Dependencies first so edits to the source do not invalidate the install layer.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen

COPY backend/ ./
COPY --from=frontend /frontend/out ./static

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# SQLite lives here; mounted as a named volume by the scripts.
ENV DATABASE_PATH=/app/data/pm.db
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
