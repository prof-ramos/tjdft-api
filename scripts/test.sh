#!/bin/bash
set -e

echo "🧪 Running tests..."

source .venv/bin/activate

pytest tests/ -v --cov=app --cov-report=html --cov-report=term

echo "✅ Tests complete!"