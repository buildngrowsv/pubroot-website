# Dockerfile for Pubroot MCP Server (Hosted HTTP Mode)
# 
# Builds a production-ready container for running the MCP server
# over Streamable HTTP at /mcp endpoint.
#
# Usage:
#   docker build -t pubroot-mcp .
#   docker run -p 8080:8080 -e REPO_MODE=remote pubroot-mcp
#
# Healthcheck: GET /healthz
# MCP endpoint: POST /mcp

FROM python:3.11-slim

LABEL org.opencontainers.image.title="Pubroot MCP Server"
LABEL org.opencontainers.image.description="MCP server for Pubroot AI peer-reviewed knowledge base"
LABEL org.opencontainers.image.source="https://github.com/buildngrowsv/pubroot-website"
LABEL org.opencontainers.image.licenses="MIT"

# Set working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install Python dependencies
# Pin exact versions from pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash pubroot && \
    chown -R pubroot:pubroot /app

USER pubroot

# Environment defaults (override at runtime)
ENV REPO_MODE=remote \
    PUBROOT_BASE=https://pubroot.com \
    GITHUB_REPO=buildngrowsv/pubroot-website \
    CACHE_TTL_SECONDS=600 \
    STALE_IF_ERROR_SECONDS=86400 \
    RATE_LIMIT_GENERAL=60 \
    RATE_LIMIT_PREPARE=10 \
    HTTP_MODE=1 \
    HTTP_HOST=0.0.0.0 \
    HTTP_PORT=8080 \
    LOG_LEVEL=INFO

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/healthz', timeout=2).raise_for_status()"

# Run the MCP server in HTTP mode
CMD ["python", "-m", "pubroot.mcp_server"]
