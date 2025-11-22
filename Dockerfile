FROM docker.io/library/python:3.12-slim-trixie@sha256:2e683fc3e18a248aa23b8022f2a3474b072b04fb851efe9b49f6b516a8944939

COPY --from=ghcr.io/astral-sh/uv:0.9.11@sha256:5aa820129de0a600924f166aec9cb51613b15b68f1dcd2a02f31a500d2ede568 /uv /uvx /bin/

# Install dependencies
# 1. git (required for caldav dependency from git)
# 2. sqlite for development with token db
RUN apt update && apt install --no-install-recommends --no-install-suggests -y \
    git \
    sqlite3 && apt clean

WORKDIR /app

COPY . .

RUN uv sync --locked --no-dev --no-editable --no-cache

ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/app/.venv
ENV PORT=8081
ENV PATH="/app/.venv/bin:$PATH"

# For Smithery deployment, use the entry point script
# For standard deployment, you can override with: docker run ... nextcloud-mcp-server --host 0.0.0.0
ENTRYPOINT ["/app/.venv/bin/python", "smithery_entrypoint.py"]
