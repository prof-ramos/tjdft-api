.PHONY: help install test lint format clean docker

help: ## Mostra essa ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependências
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test: ## Roda testes
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

lint: ## Checa código
	black --check app/ tests/
	ruff check app/ tests/
	mypy app/

format: ## Formata código
	black app/ tests/
	ruff check --fix app/ tests/

clean: ## Limpa arquivos temporários
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

docker: ## Sobe containers
	docker-compose up -d --build

docker-down: ## Para containers
	docker-compose down