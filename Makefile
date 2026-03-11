# TJDFT API Docker Makefile
# Supports multi-architecture builds for M3 (ARM64) and VPS (AMD64)

.PHONY: help build build-arm64 build-amd64 buildx push test clean dev prod dev-tools down logs logs-api shell db-shell vps-build vps-save vps-load

# Variables
IMAGE_NAME = tjdft-api
REGISTRY = gabrielramosprof
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
PLATFORMS = linux/amd64,linux/arm64

help: ## Show this help message
	@echo "TJDFT API - Docker commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build image for current platform
	docker build -t $(IMAGE_NAME):$(VERSION) .
	docker tag $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):latest

build-amd64: ## Build for AMD64 (VPS deployment)
	docker build --platform linux/amd64 -t $(IMAGE_NAME):$(VERSION)-amd64 .
	docker tag $(IMAGE_NAME):$(VERSION)-amd64 $(IMAGE_NAME):amd64

build-arm64: ## Build for ARM64 (Mac M3)
	docker build --platform linux/arm64 -t $(IMAGE_NAME):$(VERSION)-arm64 .
	docker tag $(IMAGE_NAME):$(VERSION)-arm64 $(IMAGE_NAME):arm64

buildx: ## Build and push multi-architecture image
	docker buildx create --use --name $(IMAGE_NAME)-builder 2>/dev/null || true
	docker buildx build --platform $(PLATFORMS) \
		-t $(IMAGE_NAME):$(VERSION) \
		-t $(IMAGE_NAME):latest \
		--push .

push: buildx ## Alias para buildx que já faz push

dev: ## Start development environment with hot reload
	docker compose -f docker-compose.dev.yml up --build

dev-tools: ## Start dev environment with Redis UI
	docker compose -f docker-compose.dev.yml --profile tools up --build

prod: ## Start production environment
	docker compose up -d --build

prod-nginx: ## Start production with Nginx reverse proxy
	docker compose --profile with-nginx up -d --build

down: ## Stop all services
	docker compose down
	docker compose -f docker-compose.dev.yml down

logs: ## View logs from all services
	docker compose logs -f

logs-api: ## View API logs only
	docker compose logs -f api

test: ## Run tests inside container
	docker run --rm -v "$(PWD)/tests:/app/tests" -w /app $(IMAGE_NAME):latest pytest

clean: ## Remove all containers, images, and volumes
	docker compose down -v
	docker compose -f docker-compose.dev.yml down -v
	docker image prune -f

shell: ## Open shell in running API container
	docker compose exec api sh

db-shell: ## Open SQLite shell in running container
	docker compose exec api sqlite3 /app/data/tjdft.db

# VPS deployment helpers
vps-build: ## Build for VPS (AMD64)
	docker build --platform linux/amd64 -t $(IMAGE_NAME):latest .

vps-save: ## Save image to tar file for transfer to VPS
	docker save $(IMAGE_NAME):latest | gzip > $(IMAGE_NAME)-$(VERSION).tar.gz

vps-load: ## Load image from tar file on VPS
	gunzip -c $(IMAGE_NAME)-$(VERSION).tar.gz | docker load
