# Hosted MCP Testing Commands

Quick reference for testing the hosted MCP implementation locally.

## Branch Information

- **Branch**: `cursor/hosted-mcp-streamable-http-e4a9`
- **Base Branch**: `cursor/agent-distribution-mcp-packaging-e4a9`
- **Pull Request**: #248 - https://github.com/buildngrowsv/pubroot-website/pull/248
- **Parent PR**: #247 - https://github.com/buildngrowsv/pubroot-website/pull/247

## Quick Start

```bash
# Clone and checkout the branch
git fetch origin
git checkout cursor/hosted-mcp-streamable-http-e4a9

# Install the package
pip install -e .
```

## Test 1: Stdio Mode (Unchanged)

```bash
# Start the MCP server in stdio mode
pubroot mcp --mode remote

# Should start and wait for MCP protocol messages on stdin
# Press Ctrl+C to stop

# Test with local data
pubroot mcp --mode local --local-path /path/to/pubroot-website
```

## Test 2: HTTP Mode (New)

```bash
# Start HTTP server on port 8080
pubroot mcp --http --port 8080

# In another terminal, test the health endpoint
curl http://localhost:8080/healthz

# Expected response:
# {
#   "status": "ok",
#   "service": "pubroot-mcp",
#   "version": "0.2.0",
#   "mode": "remote",
#   "cache_entries": 0
# }

# Test with custom port
pubroot mcp --http --port 3456
```

## Test 3: Run Automated Tests

```bash
# Install test dependencies
pip install -e .[test]

# Run all tests
pytest tests/ -v

# Run only HTTP transport tests
pytest tests/test_mcp_http.py -v

# Run only deployment tests
pytest tests/test_deployment.py -v

# Expected: All tests pass (5 in test_mcp_http.py, 3 in test_deployment.py)
```

## Test 4: Docker Build

```bash
# Build the Docker image
docker build -t pubroot-mcp:test .

# Expected: Build succeeds, final image ~200-300MB

# Run the container
docker run -p 8080:8080 pubroot-mcp:test

# In another terminal, test it
curl http://localhost:8080/healthz

# Stop the container
docker ps  # Find container ID
docker stop <container-id>
```

## Test 5: Docker with Custom Config

```bash
# Run with custom cache TTL and rate limits
docker run -p 3456:3456 \
  -e REPO_MODE=remote \
  -e HTTP_PORT=3456 \
  -e CACHE_TTL_SECONDS=300 \
  -e RATE_LIMIT_GENERAL=100 \
  -e RATE_LIMIT_PREPARE=20 \
  pubroot-mcp:test

# Test on custom port
curl http://localhost:3456/healthz
```

## Test 6: MCP Client Integration

For testing with an actual MCP client (e.g., Claude Desktop):

### Stdio Mode Config (mcp.json)

```json
{
  "mcpServers": {
    "pubroot": {
      "command": "uvx",
      "args": ["pubroot", "mcp"],
      "env": {
        "REPO_MODE": "remote"
      }
    }
  }
}
```

### HTTP Mode Config (mcp.json)

When the server is deployed to `https://mcp.pubroot.com`:

```json
{
  "mcpServers": {
    "pubroot-hosted": {
      "url": "https://mcp.pubroot.com/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## Test 7: Rate Limiting

```bash
# Start server
pubroot mcp --http --port 8080

# In another terminal, send rapid requests (requires MCP client or custom script)
# The server should return HTTP 429 after 60 requests per minute
# For prepare_submission, limit is 10/minute
```

## Test 8: Cache Behavior

```bash
# Start server with short cache TTL for testing
CACHE_TTL_SECONDS=5 pubroot mcp --http --port 8080

# Check logs to see cache hits and misses
# First request: cache miss (fetches from pubroot.com)
# Second request within 5s: cache hit
# Request after 5s: cache expired, refetch
```

## Test 9: Stale-If-Error

```bash
# Start server
pubroot mcp --http --port 8080

# Make a request to populate cache
# Then disconnect network or change PUBROOT_BASE to invalid URL
# Server should still serve stale data (up to 24 hours old)
```

## Verification Checklist

- [ ] `pip install -e .` succeeds
- [ ] `pubroot mcp --mode remote` starts in stdio mode
- [ ] `pubroot mcp --http --port 8080` starts HTTP server
- [ ] `/healthz` endpoint returns status ok
- [ ] `pytest tests/ -v` all tests pass
- [ ] Docker image builds successfully
- [ ] Docker container runs and responds to health checks
- [ ] MCP client can connect over stdio
- [ ] Rate limiting works (429 after limits)
- [ ] Cache reduces redundant fetches
- [ ] Logs show only tool/status/latency (no IPs or content)

## Known Limitations

1. **Docker not available in CI**: The Docker build test will skip if Docker is not installed
2. **MCP client testing**: Requires a full MCP client (Claude Desktop, etc.) for end-to-end testing
3. **Rate limiting precision**: Uses minute-bucket sliding window, not exact second-level precision
4. **Cache is in-memory**: Restarting the server clears the cache

## Troubleshooting

### Server won't start

```bash
# Check for import errors
pubroot mcp --http 2>&1 | head -n 50

# Verify dependencies
pip install -e .
```

### Tests fail

```bash
# Reinstall with test dependencies
pip install -e .[test]

# Run with verbose output
pytest tests/ -vv --tb=short
```

### Docker build fails

```bash
# Check Dockerfile syntax
cat Dockerfile

# Try building with verbose output
docker build --no-cache -t pubroot-mcp:test .
```

## Deployment Readiness

This implementation is ready for deployment when Adam approves:

✅ HTTP server works locally  
✅ All tests pass  
✅ Docker image builds  
✅ Health endpoint works  
✅ Rate limiting implemented  
✅ Privacy-safe logging  
✅ Documentation complete  
✅ fly.toml configured  

⚠️ NOT deployed yet - awaiting approval  
⚠️ No Fly app created  
⚠️ No DNS configured  

## Contact

For issues or questions:
- Open an issue at: https://github.com/buildngrowsv/pubroot-website/issues
- See: HOSTED_MCP_DEPLOYMENT.md for full documentation
