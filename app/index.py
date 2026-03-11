"""Vercel entrypoint for the FastAPI application."""

from app.main import app  # noqa: F401 (Vercel expects this export)
