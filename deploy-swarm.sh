#!/bin/bash
# Deploy TJDFT API to Docker Swarm via Portainer
# Usage: ./deploy-swarm.sh [version]

set -e

# Configuration
IMAGE_NAME="tjdft-api"
REGISTRY="gabrielramosprof"
VERSION=${1:-latest}
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$VERSION"
STACK_NAME="tjdft"
BUILDER_NAME="${IMAGE_NAME}-builder"

# Cleanup on exit
trap "docker buildx rm $BUILDER_NAME 2>/dev/null || true" EXIT

echo "=========================================="
echo "TJDFT API - Docker Swarm Deployment"
echo "=========================================="
echo "Registry: $REGISTRY"
echo "Image: $IMAGE_NAME"
echo "Version: $VERSION"
echo ""

# Pre-flight checks
if ! command -v docker &> /dev/null; then
  echo "ERROR: docker not found. Please install Docker."
  exit 1
fi

if [ ! -f "docker-compose.swarm.yml" ]; then
  echo "ERROR: docker-compose.swarm.yml not found!"
  exit 1
fi

# Build multi-arch image
echo "Step 1: Building multi-arch image..."
if docker buildx inspect $BUILDER_NAME &> /dev/null; then
  echo "Using existing builder: $BUILDER_NAME"
else
  docker buildx create --use --name $BUILDER_NAME
fi

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t $FULL_IMAGE \
  -t $REGISTRY/$IMAGE_NAME:latest \
  --push \
  .

echo ""
echo "Step 2: Deploying to Swarm..."
echo "IMPORTANT: Update domínios em docker-compose.swarm.yml antes do deploy!"
echo ""

# Deploy stack (docker stack deploy already updates existing stacks)
echo "Deploying stack '$STACK_NAME'..."
docker stack deploy -c docker-compose.swarm.yml "$STACK_NAME"

echo ""
echo "Step 3: Checking services..."
docker stack services "$STACK_NAME"

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "Monitor logs with:"
echo "  docker service logs -f ${STACK_NAME}_api"
echo ""
echo "Check service status:"
echo "  docker stack ps $STACK_NAME"
echo ""
echo "No Portainer:"
echo "  1. Vá em Stacks"
echo "  2. Encontre '$STACK_NAME'"
echo "  3. Veja status e logs"

