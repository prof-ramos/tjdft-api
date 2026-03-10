# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `app/`. Keep HTTP routes in `app/api/v1/endpoints/`, business logic in `app/services/`, persistence in `app/repositories/`, SQLAlchemy models in `app/models/`, and Pydantic schemas in `app/schemas/`. Shared helpers belong in `app/utils/`. Database migrations live in `alembic/versions/`. Tests mirror the app layout under `tests/` (`tests/test_api/`, `tests/test_services/`, etc.). Reference data and API notes live in `data/` and `docs/`.

## Build, Test, and Development Commands
Use `uv` for all Python workflows.

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload
uv run pytest
uv run pytest tests/test_services/test_tjdft_client.py -v
uv run black . && uv run isort . && uv run flake8 app tests && uv run mypy app
uv run alembic upgrade head
```

The server starts at `http://127.0.0.1:8000`, with docs at `/docs`. Run migrations before testing database-backed changes.

## Coding Style & Naming Conventions
Target Python 3.11+ with 4-space indentation and a maximum line length of 88. Format with Black and keep imports sorted with isort (`profile = "black"`). Prefer type hints on public functions and keep mypy clean for `app/`. Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; and descriptive names like `busca_service.py` or `test_enrichment.py`.

## Testing Guidelines
Pytest is configured in `pyproject.toml` with automatic coverage for `app/`. Name files `test_*.py` or `*_test.py`, classes `Test*`, and functions `test_*`. Add tests alongside the relevant layer: endpoint behavior in `tests/test_api/`, service rules in `tests/test_services/`, and utilities in `tests/test_utils/`. For every bug fix or feature, include at least one regression or behavior test.

## Commit & Pull Request Guidelines
The current history uses short, imperative messages with a prefix, e.g. `docs: improve README with TJDFT API specific information`. Follow the same `type: summary` pattern (`feat:`, `fix:`, `docs:`, `test:`). PRs should include a concise description, linked issue when applicable, test evidence (`uv run pytest` output or equivalent), and sample requests/responses for API changes.

## Security & Configuration Tips
Copy `.env.example` to `.env` and never commit secrets. Validate changes against both local config and migrations when touching `DATABASE_URL`. If you add external integrations, keep credentials in environment variables and document any new required keys in `README.md`.
