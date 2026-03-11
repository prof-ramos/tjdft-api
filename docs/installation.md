# Instalação

## Requisitos

- Python 3.11+
- Redis (opcional, para cache)

## Quick Start

```bash
# Clone
git clone https://github.com/prof-ramos/tjdft-api
cd tjdft-api

# Virtual environment
python -m venv .venv
source .venv/bin/activate

# Install
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configure
cp .env.example .env
# Edite .env com suas configurações

# Run
uvicorn app.main:app --reload
```

## Docker

```bash
docker-compose up -d
```

## Variáveis de Ambiente

| Variável | Descrição | Default |
|----------|-----------|---------|
| DATABASE_URL | URL do banco | sqlite+aiosqlite:///./data/tjdft.db |
| REDIS_URL | URL do Redis | (vazio) |
| DEBUG | Modo debug | false |