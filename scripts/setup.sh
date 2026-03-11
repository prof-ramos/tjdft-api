#!/bin/bash
set -e

echo "🚀 Setting up TJDFT API..."

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Create data directory
mkdir -p data

# Copy env example
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file"
fi

# Install pre-commit
pre-commit install

echo "✅ Setup complete!"
echo "Run: uvicorn app.main:app --reload"