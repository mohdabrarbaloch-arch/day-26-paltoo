"""Vercel serverless entrypoint. Keeps the whole app in one function.

Vercel's filesystem is ephemeral and read-only, so the app falls back to a
writable /tmp SQLite database. For a persistent multi-instance deployment,
point DATABASE_URL at a managed Postgres (see docker-compose.yml).
"""

import os

os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/paltoo.db")

from app.main import app  # noqa: E402

handler = app
