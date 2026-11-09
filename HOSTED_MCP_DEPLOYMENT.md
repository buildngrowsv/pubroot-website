# Hosted MCP Deployment Guide

This document describes how to deploy the Pubroot MCP server for hosted access via Streamable HTTP.

## Overview

The Pubroot MCP server can run in two modes:

1. **Stdio mode** (default): For local agent integration. Agents spawn the process and communicate over stdin/stdout.
2. **HTTP mode**: For hosted deployment. The server listens on HTTP and serves MCP over Streamable HTTP.

## Local Testing

### Stdio Mode (Default)

```bash
# Install in development mode
pip install -e .

# Start the server (stdio)
pubroot mcp --mode remote

# Or with local data
pubroot mcp --mode local --local-path /path/to/pubroot-website
```

### HTTP Mode

```bash
# Start HTTP server on port 8080
pubroot mcp --http --port 8080

# With custom host and port
pubroot mcp --http --host 0.0.0.0 --port 3456

# Check health
curl http://localhost:8080/healthz

# Test MCP endpoint (requires MCP client)
# The endpoint is at http://localhost:8080/mcp
```

## Docker Testing

```bash
# Build the image
docker build -t pubroot-mcp .

# Run locally
docker run -p 8080:8080 -e REPO_MODE=remote pubroot-mcp

# Test health
curl http://localhost:8080/healthz

# Run with custom config
docker run -p 3456:3456 \
  -e REPO_MODE=remote \
  -e HTTP_PORT=3456 \
  -e CACHE_TTL_SECONDS=300 \
  -e RATE_LIMIT_GENERAL=100 \
  pubroot-mcp
```

## Fly.io Deployment

**IMPORTANT**: Do NOT deploy to production yet. This is prepared for when Adam approves.

### Prerequisites

1. Install Fly CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Authenticate: `fly auth login`
3. Choose an organization or create one

### Setup Steps

```bash
# Create the Fly app (one-time)
fly apps create pubroot-mcp --org <your-org>

# Deploy (from repo root)
fly deploy --config deploy/fly/fly.toml

# Check status
fly status

# View logs
fly logs

# Open the app
fly open /healthz
```

### Custom Domain Setup

```bash
# Add DNS record: mcp.pubroot.com CNAME <app-name>.fly.dev
# Then create the certificate
fly certs create mcp.pubroot.com

# Check certificate status
fly certs show mcp.pubroot.com
```

### Scaling

```bash
# Scale to dedicated CPU with more memory
fly scale vm dedicated-cpu-1x --memory 512

# Scale instances
fly scale count 2

# Auto-scale (in fly.toml)
# Set min_machines_running and max_machines_running
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REPO_MODE` | `local` | Data source: `local` or `remote` |
| `PUBROOT_BASE` | `https://pubroot.com` | Base URL for remote data |
| `GITHUB_REPO` | `buildngrowsv/pubroot-website` | GitHub repo for fallback |
| `CACHE_TTL_SECONDS` | `600` | Cache TTL (10 minutes) |
| `STALE_IF_ERROR_SECONDS` | `86400` | Stale cache lifetime (24 hours) |
| `RATE_LIMIT_GENERAL` | `60` | General rate limit (requests per minute per IP) |
| `RATE_LIMIT_PREPARE` | `10` | prepare_submission rate limit (per minute per IP) |
| `HTTP_MODE` | `0` | Set to `1` to enable HTTP mode |
| `HTTP_HOST` | `0.0.0.0` | HTTP server host |
| `HTTP_PORT` | `8080` | HTTP server port |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### Rate Limiting

The HTTP server implements per-IP rate limiting:

- **General tools** (search, verify, etc.): 60 requests/minute per IP
- **prepare_submission**: 10 requests/minute per IP (stricter due to GitHub issue URL generation)

Rate limits are enforced using sliding window counters per minute.

### Caching

The server caches remote data fetches with:

- **10-minute TTL**: Fresh data is cached for 10 minutes
- **Stale-if-error (24 hours)**: If a fetch fails, serve stale data up to 24 hours old
- **Domain allow-list**: Only `pubroot.com` and `raw.githubusercontent.com` are allowed

### Privacy & Logging

The hosted server logs only:

- Tool name (e.g., `search_papers`)
- HTTP status code
- Request latency (milliseconds)

It does NOT log:

- Client IP addresses (only last 8 characters in rate limit warnings)
- Query text or search terms
- Draft submission content
- Any user data

This ensures privacy compliance while maintaining operational visibility.

## Security

### No Secrets Required

The MCP server reads public data only and requires no secrets or API keys.

### No Write Operations

All tools are read-only except `prepare_submission`, which only generates URLs without creating GitHub issues.

### Size Limits

- **Request size**: 1MB maximum
- **Response size**: 10MB maximum (enforced by application logic)

### Domain Restrictions

Outbound fetches are restricted to:

- `pubroot.com` (primary data source)
- `raw.githubusercontent.com` (fallback)

## Testing

### Run Tests Locally

```bash
# Install test dependencies
pip install -e .[test]

# Run all tests
pytest tests/ -v

# Run HTTP transport tests only
pytest tests/test_mcp_http.py -v

# Run deployment tests (requires Docker)
pytest tests/test_deployment.py -v
```

### Manual MCP Testing

The server can be tested with any MCP client. Example using the MCP inspector:

```bash
# Start server in HTTP mode
pubroot mcp --http --port 8080

# In another terminal, use an MCP client to connect to:
# http://localhost:8080/mcp
```

## Monitoring

### Health Checks

```bash
# Basic health check
curl http://localhost:8080/healthz

# Expected response:
{
  "status": "ok",
  "service": "pubroot-mcp",
  "version": "0.2.0",
  "mode": "remote",
  "cache_entries": 5
}
```

### Fly.io Monitoring

```bash
# View metrics
fly dashboard

# View logs
fly logs

# SSH into instance
fly ssh console
```

## Troubleshooting

### Server Won't Start

Check logs for import errors:

```bash
pubroot mcp --http 2>&1 | head -n 50
```

### Rate Limiting Issues

Temporarily increase limits:

```bash
RATE_LIMIT_GENERAL=120 RATE_LIMIT_PREPARE=20 pubroot mcp --http
```

### Cache Issues

Clear the cache by restarting the server. The cache is in-memory only.

### Docker Build Fails

Ensure all dependencies are in `pyproject.toml` and the Dockerfile copies the correct files.

## Cost Estimates

### Fly.io Pricing (as of 2026)

- **Free tier**: 1 shared-cpu-1x VM with 256MB RAM (sufficient for low traffic)
- **Dedicated**: ~$5-10/month for dedicated-cpu-1x with 512MB RAM
- **Bandwidth**: Generous free tier, then ~$0.02/GB

For the Pubroot MCP server (read-only, cached data), the free tier should suffice unless traffic exceeds several thousand requests per day.

## Production Checklist

Before deploying to production:

- [ ] Adam approves the deployment
- [ ] DNS for mcp.pubroot.com is ready
- [ ] Fly app is created and configured
- [ ] Docker image builds successfully (`docker build -t pubroot-mcp .`)
- [ ] Local HTTP mode tested (`pubroot mcp --http`)
- [ ] Health check works (`/healthz`)
- [ ] Rate limiting tested
- [ ] MCP tools tested via MCP client
- [ ] Tests pass (`pytest tests/ -v`)
- [ ] `server.json` updated with remotes entry
- [ ] Monitoring/alerting configured (optional)

## Support

For issues with the MCP server:

1. Check logs: `fly logs` or `docker logs <container>`
2. Verify health: `curl http://<host>/healthz`
3. Test locally first: `pubroot mcp --http --port 8080`
4. Open an issue at: https://github.com/buildngrowsv/pubroot-website/issues
