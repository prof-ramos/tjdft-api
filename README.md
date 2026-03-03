# TJDFT API

FastAPI application with SQLAlchemy and Pydantic.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Running

Development server:
```bash
uvicorn app.main:app --reload
```

Production server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Testing

Run tests:
```bash
pytest
pytest --cov=app
```

## Code Quality

Format code:
```bash
black .
isort .
```

Check formatting:
```bash
black --check .
isort --check-only .
```

Lint:
```bash
flake8
mypy app/
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
