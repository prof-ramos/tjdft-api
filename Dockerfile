# Multi-architecture Dockerfile for TJDFT API
# Supports: linux/amd64 (VPS) and linux/arm64 (Mac M3)

# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.11-slim AS builder

# Install build dependencies for native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies to a temporary location
# --no-cache-dir: smaller image
# --upgrade: ensure latest compatible versions (for pip, setuptools, wheel only)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Runtime
# ==========================================
FROM python:3.11-slim AS runtime

# Set architecture labels
LABEL maintainer="prof-ramos"
LABEL description="TJDFT API - Jurisprudência do Tribunal de Justiça do DF"
LABEL version="1.0.0"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r tjdft && useradd -r -g tjdft tjdft

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY pyproject.toml ./

# Create directory for SQLite database with proper permissions
RUN mkdir -p /app/data && \
    chown -R tjdft:tjdft /app

# Switch to non-root user
USER tjdft

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set default environment variables (can be overridden)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_URL=sqlite+aiosqlite:////app/data/tjdft.db \
    REDIS_URL=redis://redis:6379 \
    CACHE_TTL=3600 \
    DEBUG=false

# Run the application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
