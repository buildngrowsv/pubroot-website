"""
Tests for deployment configuration.

Verifies that Dockerfile and fly.toml are valid and the server
can be built and run locally.
"""

import os
import subprocess
import pytest


def test_dockerfile_exists():
    """Verify Dockerfile exists and has basic structure."""
    dockerfile_path = os.path.join(os.path.dirname(__file__), '..', 'Dockerfile')
    assert os.path.exists(dockerfile_path), "Dockerfile not found"
    
    with open(dockerfile_path) as f:
        content = f.read()
        
    # Check for required sections
    assert 'FROM python:' in content
    assert 'COPY pyproject.toml' in content
    assert 'pip install' in content
    assert 'EXPOSE 8080' in content
    assert 'HEALTHCHECK' in content
    assert 'CMD' in content or 'ENTRYPOINT' in content


def test_fly_toml_exists():
    """Verify fly.toml exists and has basic structure."""
    fly_toml_path = os.path.join(os.path.dirname(__file__), '..', 'deploy', 'fly', 'fly.toml')
    assert os.path.exists(fly_toml_path), "fly.toml not found"
    
    with open(fly_toml_path) as f:
        content = f.read()
    
    # Check for required sections
    assert 'app =' in content
    assert '[build]' in content
    assert 'dockerfile' in content.lower()
    assert '[http_service]' in content or '[[services]]' in content
    assert 'internal_port = 8080' in content


def test_dockerignore_exists():
    """Verify .dockerignore exists."""
    dockerignore_path = os.path.join(os.path.dirname(__file__), '..', '.dockerignore')
    assert os.path.exists(dockerignore_path), ".dockerignore not found"


@pytest.mark.skipif(
    subprocess.run(['which', 'docker'], capture_output=True).returncode != 0,
    reason="Docker not available"
)
def test_docker_build():
    """Test that Docker image can be built (if Docker is available)."""
    project_root = os.path.join(os.path.dirname(__file__), '..')
    
    # Try to build the image
    result = subprocess.run(
        ['docker', 'build', '-t', 'pubroot-mcp:test', '.'],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )
    
    print("Docker build stdout:", result.stdout)
    print("Docker build stderr:", result.stderr)
    
    assert result.returncode == 0, f"Docker build failed: {result.stderr}"
    
    # Verify image exists
    result = subprocess.run(
        ['docker', 'images', 'pubroot-mcp:test'],
        capture_output=True,
        text=True
    )
    assert 'pubroot-mcp' in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
