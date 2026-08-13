FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Dependencies first so edits to the source do not invalidate the install layer.
COPY backend/pyproject.toml ./
RUN uv sync

COPY backend/ ./

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# SQLite lives here from Part 6 onward; mounted as a named volume by the scripts.
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
