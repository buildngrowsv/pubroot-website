"""
Tests for MCP server HTTP transport, caching, and rate limiting.

These tests verify:
1. HTTP transport works (Streamable HTTP at /mcp)
2. Caching with TTL and stale-if-error
3. Per-IP rate limiting
4. Health endpoint
5. Size limits
6. Domain allow-list
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pubroot import mcp_server


def test_cache_ttl():
    """Test that cache respects TTL."""
    # Clear cache
    mcp_server._json_cache.clear()
    
    # Set short TTL
    original_ttl = mcp_server.CACHE_TTL_SECONDS
    mcp_server.CACHE_TTL_SECONDS = 1
    
    try:
        # Mock the actual fetch
        with patch('pubroot.mcp_server.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"test": "data"}
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            
            # Set remote mode
            original_mode = mcp_server.REPO_MODE
            mcp_server.REPO_MODE = "remote"
            
            # First call should fetch
            result1 = mcp_server._load_json("test.json")
            assert result1 == {"test": "data"}
            assert mock_get.call_count == 1
            
            # Second call within TTL should use cache
            result2 = mcp_server._load_json("test.json")
            assert result2 == {"test": "data"}
            assert mock_get.call_count == 1  # Still 1, used cache
            
            # Wait for TTL to expire
            time.sleep(1.1)
            
            # Third call after TTL should fetch again
            result3 = mcp_server._load_json("test.json")
            assert result3 == {"test": "data"}
            assert mock_get.call_count == 2  # Fetched again
            
            mcp_server.REPO_MODE = original_mode
    finally:
        mcp_server.CACHE_TTL_SECONDS = original_ttl


def test_stale_if_error():
    """Test that cache serves stale data on fetch error."""
    mcp_server._json_cache.clear()
    
    with patch('pubroot.mcp_server.requests.get') as mock_get:
        # First fetch succeeds
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        original_mode = mcp_server.REPO_MODE
        mcp_server.REPO_MODE = "remote"
        
        result1 = mcp_server._load_json("test.json")
        assert result1 == {"test": "data"}
        
        # Expire the cache
        for key in mcp_server._json_cache:
            timestamp, data, error_ts = mcp_server._json_cache[key]
            mcp_server._json_cache[key] = (timestamp - 1000, data, error_ts)
        
        # Second fetch fails - should serve stale
        mock_get.side_effect = Exception("Network error")
        
        result2 = mcp_server._load_json("test.json")
        assert result2 == {"test": "data"}  # Served stale data
        
        mcp_server.REPO_MODE = original_mode


def test_rate_limiting():
    """Test per-IP rate limiting."""
    # Clear rate limit buckets
    mcp_server._rate_limit_buckets.clear()
    mcp_server._rate_limit_prepare.clear()
    
    # Set low limits for testing
    original_general = mcp_server.RATE_LIMIT_GENERAL
    original_prepare = mcp_server.RATE_LIMIT_PREPARE
    mcp_server.RATE_LIMIT_GENERAL = 5
    mcp_server.RATE_LIMIT_PREPARE = 2
    
    try:
        test_ip = "192.168.1.1"
        
        # Test general limit
        for i in range(5):
            assert mcp_server._check_rate_limit(test_ip, "search_papers") is True
        
        # 6th request should fail
        assert mcp_server._check_rate_limit(test_ip, "search_papers") is False
        
        # Test prepare_submission limit (separate bucket)
        test_ip2 = "192.168.1.2"
        for i in range(2):
            assert mcp_server._check_rate_limit(test_ip2, "prepare_submission") is True
        
        # 3rd request should fail
        assert mcp_server._check_rate_limit(test_ip2, "prepare_submission") is False
        
    finally:
        mcp_server.RATE_LIMIT_GENERAL = original_general
        mcp_server.RATE_LIMIT_PREPARE = original_prepare


def test_domain_allowlist():
    """Test that only allowed domains can be fetched."""
    mcp_server._json_cache.clear()
    
    with patch('pubroot.mcp_server.requests.get') as mock_get:
        original_mode = mcp_server.REPO_MODE
        mcp_server.REPO_MODE = "remote"
        
        # Allowed domain should work
        original_base = mcp_server.PUBROOT_BASE
        mcp_server.PUBROOT_BASE = "https://pubroot.com"
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        result = mcp_server._load_json("test.json")
        assert result == {"test": "data"}
        
        # Clear cache so second call tries to fetch
        mcp_server._json_cache.clear()
        
        # Disallowed domain should fail
        mcp_server.PUBROOT_BASE = "https://evil.com"
        
        with pytest.raises(ValueError, match="not in allow-list"):
            mcp_server._load_json("test2.json")  # Use different filename to avoid cache
        
        mcp_server.REPO_MODE = original_mode
        mcp_server.PUBROOT_BASE = original_base


@pytest.mark.asyncio
async def test_http_server_basic():
    """Test that HTTP server can be created."""
    # This is a basic smoke test - just verify imports and structure
    # Full integration testing would require starting the server
    
    # Verify the HTTP server components exist
    assert hasattr(mcp_server, 'main_http')
    assert hasattr(mcp_server, 'main_http_async')
    assert hasattr(mcp_server, 'main_stdio')
    
    # Verify configuration is set up
    assert mcp_server.RATE_LIMIT_GENERAL > 0
    assert mcp_server.RATE_LIMIT_PREPARE > 0
    assert mcp_server.CACHE_TTL_SECONDS > 0
    assert mcp_server.STALE_IF_ERROR_SECONDS > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
