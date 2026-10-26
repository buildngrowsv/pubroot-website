"""
Tests for Stage 3: Read Linked Repository — Pubroot Review Pipeline

HISTORY:
    Created 2026-03-23 by Builder 5 (swarm agent) as part of T4.
    These tests validate the repository cloning and reading logic that
    provides code context for the LLM reviewer.

APPROACH:
    - Git clone operations are mocked to avoid network calls and real
      filesystem cloning. We use a temp directory to simulate a cloned repo.
    - The file tree extraction and key file reading use real file I/O
      against temp directories to test actual parsing logic.
    - Each test targets a specific case documented in the stage 3 module.

RUNNING:
    pytest _review_agent/test_stage_3_read_linked_repo.py -v
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock, call

from stage_3_read_linked_repo import (
    read_linked_repository,
    _extract_file_tree,
    _read_key_files,
)


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_repo_dir(tmp_path):
    """
    Create a temp directory that simulates a cloned repository.
    Contains a realistic mix of files that the priority reader should handle.
    """
    # README
    readme = tmp_path / "README.md"
    readme.write_text("# My Project\n\nA sample project for testing.\n")

    # Requirements
    reqs = tmp_path / "requirements.txt"
    reqs.write_text("requests>=2.31.0\npytest>=8.0.0\n")

    # Main entry point
    main_py = tmp_path / "main.py"
    main_py.write_text('"""Main entry point."""\n\ndef main():\n    print("hello")\n\nif __name__ == "__main__":\n    main()\n')

    # Source directory
    src = tmp_path / "src"
    src.mkdir()

    # Source files
    utils_py = src / "utils.py"
    utils_py.write_text('"""Utility functions."""\n\ndef add(a, b):\n    return a + b\n')

    config_py = src / "config.py"
    config_py.write_text('"""Configuration."""\nDEBUG = False\n')

    # Config file
    config_toml = tmp_path / "pyproject.toml"
    config_toml.write_text('[project]\nname = "myproject"\nversion = "1.0.0"\n')

    # .git directory (should be excluded from tree)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")

    # node_modules (should be excluded)
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "package.json").write_text("{}")

    # Binary-like file (should be excluded by extension)
    (tmp_path / "data.db").write_text("binary data")

    # __pycache__ (should be excluded)
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "main.cpython-311.pyc").write_bytes(b"\x00\x00\x00\x00")

    return tmp_path


# ---------------------------------------------------------------------------
# NO-REPO / PRIVATE REPO CASES (no network calls needed)
# ---------------------------------------------------------------------------


class TestNoRepoSubmissions:
    """Test handling of submissions without a supporting repository."""

    def test_no_repo_url_returns_text_only(self):
        """When repo_url is None, should return text_only badge with no errors."""
        result = read_linked_repository(
            repo_url=None,
            commit_sha=None,
            repo_visibility="no-repo",
        )

        assert result["available"] is False
        assert result["visibility"] == "no-repo"
        assert result["badge_type"] == "text_only"
        assert result["file_tree"] == ""
        assert result["file_count"] == 0
        assert result["key_files"] == []
        assert result["errors"] == []

    def test_empty_repo_url_returns_text_only(self):
        """When repo_url is empty string, should return text_only."""
        result = read_linked_repository(
            repo_url="",
            commit_sha=None,
            repo_visibility="public",
        )

        assert result["available"] is False
        assert result["badge_type"] == "text_only"

    def test_no_repo_visibility_returns_text_only(self):
        """When visibility is 'no-repo', should return text_only even if URL is given."""
        result = read_linked_repository(
            repo_url="https://github.com/owner/repo",
            commit_sha=None,
            repo_visibility="no-repo",
        )

        assert result["available"] is False
        assert result["badge_type"] == "text_only"


class TestPrivateRepoSubmissions:
    """Test handling of private repository submissions (deferred feature)."""

    def test_private_repo_returns_verified_private(self):
        """Private repos should return verified_private badge with a note."""
        result = read_linked_repository(
            repo_url="https://github.com/owner/private-repo",
            commit_sha=None,
            repo_visibility="private",
        )

        assert result["available"] is False
        assert result["visibility"] == "private"
        assert result["badge_type"] == "verified_private"
        assert len(result["errors"]) == 1
        assert "not yet supported" in result["errors"][0]


# ---------------------------------------------------------------------------
# URL VALIDATION TESTS
# ---------------------------------------------------------------------------


class TestUrlValidation:
    """Test GitHub URL format validation before clone attempt."""

    @patch("stage_3_read_linked_repo.subprocess.run")
    @patch("stage_3_read_linked_repo.tempfile.mkdtemp")
    @patch("stage_3_read_linked_repo.shutil.rmtree")
    def test_invalid_url_returns_error_without_cloning(self, mock_rmtree, mock_mkdtemp, mock_run):
        """A non-GitHub URL should fail validation before any git clone."""
        result = read_linked_repository(
            repo_url="https://gitlab.com/owner/repo",
            commit_sha=None,
            repo_visibility="public",
        )

        assert result["available"] is False
        assert any("Invalid GitHub URL" in e for e in result["errors"])
        # Should NOT have attempted to clone
        mock_run.assert_not_called()

    def test_malformed_url_returns_error(self):
        """Completely malformed URLs should be caught."""
        result = read_linked_repository(
            repo_url="not-a-url-at-all",
            commit_sha=None,
            repo_visibility="public",
        )

        assert result["available"] is False
        assert any("Invalid GitHub URL" in e for e in result["errors"])

    @patch("stage_3_read_linked_repo.subprocess.run")
    @patch("stage_3_read_linked_repo.tempfile.mkdtemp", return_value="/tmp/test_repo")
    @patch("stage_3_read_linked_repo.shutil.rmtree")
    @patch("stage_3_read_linked_repo._extract_file_tree", return_value=("file.py", 1))
    @patch("stage_3_read_linked_repo._read_key_files", return_value=([], 0))
    def test_valid_github_url_accepted(self, mock_read, mock_tree, mock_rmtree, mock_mkdtemp, mock_run):
        """A valid GitHub URL should proceed to clone."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = read_linked_repository(
            repo_url="https://github.com/owner/repo",
            commit_sha=None,
            repo_visibility="public",
        )

        # Should have called git clone
        mock_run.assert_called_once()
        assert result["available"] is True

    @patch("stage_3_read_linked_repo.subprocess.run")
    @patch("stage_3_read_linked_repo.tempfile.mkdtemp", return_value="/tmp/test_repo")
    @patch("stage_3_read_linked_repo.shutil.rmtree")
    @patch("stage_3_read_linked_repo._extract_file_tree", return_value=("file.py", 1))
    @patch("stage_3_read_linked_repo._read_key_files", return_value=([], 0))
    def test_url_with_dotgit_suffix_accepted(self, mock_read, mock_tree, mock_rmtree, mock_mkdtemp, mock_run):
        """A GitHub URL ending in .git should be accepted."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = read_linked_repository(
            repo_url="https://github.com/owner/repo.git",
            commit_sha=None,
            repo_visibility="public",
        )

        assert result["available"] is True


# ---------------------------------------------------------------------------
# GIT CLONE BEHAVIOR TESTS
# ---------------------------------------------------------------------------


class TestGitCloneBehavior:
    """Test git clone command construction and error handling."""

    @patch("stage_3_read_linked_repo.subprocess.run")
    @patch("stage_3_read_linked_repo.tempfile.mkdtemp", return_value="/tmp/test_repo")
    @patch("stage_3_read_linked_repo.shutil.rmtree")
    def test_shallow_clone_when_no_commit_sha(self, mock_rmtree, mock_mkdtemp, mock_run):
        """Without a commit SHA, git clone should use --depth 1 for speed."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        # We need to also mock the file tree and key files extraction
        with patch("stage_3_read_linked_repo._extract_file_tree", return_value=("", 0)):
            with patch("stage_3_read_linked_repo._read_key_files", return_value=([], 0)):
                read_linked_repository(
                    repo_url="https://github.com/owner/repo",
                    commit_sha=None,
                    repo_visibility="public",
                )

        clone_call = mock_run.call_args_list[0]
        cmd = clone_call[0][0]
        assert "--depth" in cmd
        assert "1" in cmd

    @patch("stage_3_read_linked_repo.subprocess.run")
    @patch("stage_3_read_linked_repo.tempfile.mkdtemp", return_value="/tmp/test_repo")
    @patch("stage_3_read_linked_repo.shutil.rmtree")
    def test_full_clone_when_commit_sha_provided(self, mock_rmtree, mock_mkdtemp, mock_run):
        """With a commit SHA, git clone should NOT use --depth 1 (needs full history)."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        with patch("stage_3_read_linked_repo._extract_file_tree", return_value=("", 0)):
            with patch("stage_3_read_linked_repo._read_key_files", return_value=([], 0)):
                read_linked_repository(
                    repo_url="https://github.com/owner/repo",
                    commit_sha="abc1234",
                    repo_visibility="public",
                )

        # First call is clone, second is checkout
        clone_call = mock_run.call_args_list[0]
        cmd = clone_call[0][0]
        assert "--depth" not in cmd

        # Second call should be git checkout <sha>
        checkout_call = mock_run.call_args_list[1]
        checkout_cmd = checkout_call[0][0]
        assert "checkout" in checkout_cmd
        assert "abc1234" in checkout_cmd

    @patch("stage_3_read_linked_repo.subprocess.run")
    @patch("stage_3_read_linked_repo.tempfile.mkdtemp", return_value="/tmp/test_repo")
    @patch("stage_3_read_linked_repo.shutil.rmtree")
    def test_clone_failure_returns_error(self, mock_rmtree, mock_mkdtemp, mock_run):
        """If git clone fails, should return an error with the stderr message."""
        mock_run.return_value = MagicMock(
            returncode=128,
            stderr="fatal: repository not found",
        )

        result = read_linked_repository(
            repo_url="https://github.com/owner/nonexistent",
            commit_sha=None,
            repo_visibility="public",
        )

        assert result["available"] is False
        assert any("Failed to clone" in e for e in result["errors"])
        assert any("repository not found" in e for e in result["errors"])

    @patch("stage_3_read_linked_repo.subprocess.run")
    @patch("stage_3_read_linked_repo.tempfile.mkdtemp", return_value="/tmp/test_repo")
    @patch("stage_3_read_linked_repo.shutil.rmtree")
    def test_clone_timeout_returns_error(self, mock_rmtree, mock_mkdtemp, mock_run):
        """If git clone times out, should return a timeout error."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git clone", timeout=120)

        result = read_linked_repository(
            repo_url="https://github.com/owner/huge-repo",
            commit_sha=None,
            repo_visibility="public",
        )

        assert result["available"] is False
        assert any("timed out" in e.lower() for e in result["errors"])

    @patch("stage_3_read_linked_repo.subprocess.run")
    @patch("stage_3_read_linked_repo.tempfile.mkdtemp", return_value="/tmp/test_repo")
    @patch("stage_3_read_linked_repo.shutil.rmtree")
    def test_temp_dir_always_cleaned_up(self, mock_rmtree, mock_mkdtemp, mock_run):
        """The temp directory should ALWAYS be cleaned up, even on failure."""
        mock_run.return_value = MagicMock(returncode=128, stderr="error")

        read_linked_repository(
            repo_url="https://github.com/owner/repo",
            commit_sha=None,
            repo_visibility="public",
        )

        # shutil.rmtree should have been called to clean up
        mock_rmtree.assert_called_once_with("/tmp/test_repo", ignore_errors=True)


# ---------------------------------------------------------------------------
# _extract_file_tree TESTS (real file I/O against temp dirs)
# ---------------------------------------------------------------------------


class TestExtractFileTree:
    """Test the file tree extraction helper."""

    def test_excludes_git_directory(self, mock_repo_dir):
        """The .git directory should not appear in the file tree."""
        tree, count = _extract_file_tree(str(mock_repo_dir))

        assert ".git" not in tree
        assert "HEAD" not in tree  # .git/HEAD

    def test_excludes_node_modules(self, mock_repo_dir):
        """node_modules should not appear in the file tree."""
        tree, count = _extract_file_tree(str(mock_repo_dir))

        assert "node_modules" not in tree

    def test_excludes_pycache(self, mock_repo_dir):
        """__pycache__ should not appear in the file tree."""
        tree, count = _extract_file_tree(str(mock_repo_dir))

        assert "__pycache__" not in tree
        assert ".pyc" not in tree

    def test_excludes_binary_extensions(self, mock_repo_dir):
        """Files with binary extensions (.db, .pyc, etc.) should be excluded."""
        tree, count = _extract_file_tree(str(mock_repo_dir))

        assert "data.db" not in tree

    def test_includes_source_files(self, mock_repo_dir):
        """Python source files should be included in the tree."""
        tree, count = _extract_file_tree(str(mock_repo_dir))

        assert "main.py" in tree
        assert "utils.py" in tree
        assert "README.md" in tree

    def test_file_count_is_accurate(self, mock_repo_dir):
        """File count should reflect the number of non-excluded files."""
        tree, count = _extract_file_tree(str(mock_repo_dir))

        # Expected files: README.md, requirements.txt, main.py,
        # src/utils.py, src/config.py, pyproject.toml, .gitignore (if present)
        # Excluding: .git/*, node_modules/*, __pycache__/*, data.db
        assert count >= 5  # At least our core files

    def test_tree_capped_at_200_lines(self, tmp_path):
        """File trees with >200 files should be truncated with a message."""
        # Create 250 files
        for i in range(250):
            (tmp_path / f"file_{i:03d}.py").write_text(f"# File {i}")

        tree, count = _extract_file_tree(str(tmp_path))

        assert count == 250
        assert "and 50 more files" in tree


# ---------------------------------------------------------------------------
# _read_key_files TESTS (real file I/O)
# ---------------------------------------------------------------------------


class TestReadKeyFiles:
    """Test the priority-based file reading helper."""

    def test_readme_read_first(self, mock_repo_dir):
        """README should be the first file read (highest priority)."""
        files, total = _read_key_files(str(mock_repo_dir), max_bytes=50000)

        assert len(files) > 0
        assert files[0]["path"] == "README.md"

    def test_requirements_read_early(self, mock_repo_dir):
        """requirements.txt should be read with high priority."""
        files, total = _read_key_files(str(mock_repo_dir), max_bytes=50000)

        file_paths = [f["path"] for f in files]
        assert "requirements.txt" in file_paths

    def test_main_entry_point_included(self, mock_repo_dir):
        """main.py should be included in the key files."""
        files, total = _read_key_files(str(mock_repo_dir), max_bytes=50000)

        file_paths = [f["path"] for f in files]
        assert "main.py" in file_paths

    def test_respects_byte_limit(self, mock_repo_dir):
        """Total content should not exceed the max_bytes limit."""
        files, total = _read_key_files(str(mock_repo_dir), max_bytes=100)

        assert total <= 100

    def test_truncated_files_are_marked(self, tmp_path):
        """Files that are cut short due to byte limit should have truncated=True."""
        # Create a file larger than our tiny limit
        big_file = tmp_path / "README.md"
        big_file.write_text("Line of content\n" * 100)

        files, total = _read_key_files(str(tmp_path), max_bytes=50)

        if files:
            assert files[0]["truncated"] is True

    def test_excludes_large_individual_files(self, tmp_path):
        """Files larger than 100KB individually should be skipped."""
        # Create a file over 100KB
        big_file = tmp_path / "huge.py"
        big_file.write_text("x" * 110000)

        # Create a normal file
        small_file = tmp_path / "main.py"
        small_file.write_text('print("hello")\n')

        files, total = _read_key_files(str(tmp_path), max_bytes=50000)

        file_paths = [f["path"] for f in files]
        assert "huge.py" not in file_paths
        assert "main.py" in file_paths

    def test_excludes_non_text_extensions(self, tmp_path):
        """Files with non-text extensions should be excluded."""
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "main.py").write_text("print('hi')")

        files, total = _read_key_files(str(tmp_path), max_bytes=50000)

        file_paths = [f["path"] for f in files]
        assert "image.png" not in file_paths
        assert "main.py" in file_paths

    def test_file_size_preserved_in_output(self, mock_repo_dir):
        """Each file entry should include the original file size."""
        files, total = _read_key_files(str(mock_repo_dir), max_bytes=50000)

        for f in files:
            assert "size_bytes" in f
            assert isinstance(f["size_bytes"], int)
            assert f["size_bytes"] > 0

    def test_empty_repo_returns_empty_list(self, tmp_path):
        """An empty repo directory should return an empty file list."""
        files, total = _read_key_files(str(tmp_path), max_bytes=50000)

        assert files == []
        assert total == 0


# ---------------------------------------------------------------------------
# SECURITY TESTS: SYMLINK PROTECTION (B1 Fix Verification)
# ---------------------------------------------------------------------------


class TestSymlinkProtection:
    """
    Security tests for the symlink exfiltration vulnerability fix (B1).
    
    These tests verify that a malicious submitter cannot use symlinks to
    exfiltrate secrets or read files outside the cloned repository.
    
    ATTACK SCENARIOS TESTED:
    1. Symlink to /etc/passwd (common system file)
    2. Symlink to .git/config (would contain GITHUB_TOKEN if persist-credentials=true)
    3. Symlink to /proc/self/environ (exposes all env vars including GEMINI_API_KEY)
    4. Symlink using relative path traversal (../../../../etc/passwd)
    5. Symlink to a directory outside the repo
    
    These tests prove that the fix (symlink detection + realpath validation) blocks
    all known attack vectors for exfiltrating runner secrets via repository content.
    """
    
    def test_symlink_to_system_file_is_skipped(self, tmp_path):
        """
        SECURITY TEST: A symlink to /etc/passwd should be detected and skipped.
        
        This simulates a malicious repo with a file named "README.md" that is
        actually a symlink to /etc/passwd. Without the fix, this would read
        the password file and include it in the LLM prompt, and potentially
        in the public review comment.
        """
        # Create a normal file
        (tmp_path / "safe.py").write_text("print('safe')")
        
        # Create a symlink to a system file (if /etc/passwd exists)
        if os.path.exists("/etc/passwd"):
            passwd_link = tmp_path / "README.md"
            passwd_link.symlink_to("/etc/passwd")
            
            files, total = _read_key_files(str(tmp_path), max_bytes=50000)
            
            # README.md should NOT be in the results (it's a symlink)
            file_paths = [f["path"] for f in files]
            assert "README.md" not in file_paths
            
            # Verify the content doesn't contain /etc/passwd content
            all_content = " ".join(f["content"] for f in files)
            # /etc/passwd contains lines like "root:x:0:0:..."
            assert "root:x:0:0" not in all_content
    
    def test_symlink_to_git_config_is_skipped(self, tmp_path):
        """
        SECURITY TEST: A symlink to .git/config should be blocked.
        
        Without persist-credentials: false, actions/checkout writes the
        GITHUB_TOKEN to .git/config. A malicious repo could create a symlink
        named "config.json" pointing to ../.git/config to exfiltrate it.
        """
        # Create a fake .git/config with a token (simulating the attack target)
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        git_config = git_dir / "config"
        git_config.write_text("[http]\n\textraheader = AUTHORIZATION: basic ghp_FAKE_TOKEN_1234567890abcdefghijklmnopqrstuvwxyz\n")
        
        # Create a symlink in the repo root pointing to .git/config
        config_link = tmp_path / "config.json"
        config_link.symlink_to(git_config)
        
        files, total = _read_key_files(str(tmp_path), max_bytes=50000)
        
        # config.json should NOT be in the results
        file_paths = [f["path"] for f in files]
        assert "config.json" not in file_paths
        
        # Verify the token doesn't appear in any read content
        all_content = " ".join(f["content"] for f in files)
        assert "ghp_FAKE_TOKEN" not in all_content
    
    def test_symlink_to_proc_environ_is_skipped(self, tmp_path):
        """
        SECURITY TEST: A symlink to /proc/self/environ should be blocked.
        
        /proc/self/environ contains all environment variables, including
        GEMINI_API_KEY, GITHUB_TOKEN, and other secrets. A malicious repo
        could create a symlink to this file to exfiltrate secrets.
        
        NOTE: /proc/self/environ reports size 0 bytes, so it passes the
        100KB size filter in _read_key_files. This makes it a particularly
        dangerous target that the symlink check MUST catch.
        """
        # Create a normal file
        (tmp_path / "main.py").write_text("print('main')")
        
        # Create a symlink to /proc/self/environ (if it exists)
        if os.path.exists("/proc/self/environ"):
            environ_link = tmp_path / "environment.txt"
            environ_link.symlink_to("/proc/self/environ")
            
            files, total = _read_key_files(str(tmp_path), max_bytes=50000)
            
            # environment.txt should NOT be in the results
            file_paths = [f["path"] for f in files]
            assert "environment.txt" not in file_paths
    
    def test_relative_symlink_traversal_is_blocked(self, tmp_path):
        """
        SECURITY TEST: Symlinks using relative path traversal should be blocked.
        
        A malicious repo could use ../../../../etc/passwd to try to escape
        the repo directory. The realpath validation should catch this.
        """
        # Create a symlink using relative traversal
        if os.path.exists("/etc/passwd"):
            traversal_link = tmp_path / "data.txt"
            # Try to escape the tmp_path and reach /etc/passwd
            traversal_link.symlink_to("../../../../../../../../etc/passwd")
            
            files, total = _read_key_files(str(tmp_path), max_bytes=50000)
            
            # data.txt should NOT be in the results
            file_paths = [f["path"] for f in files]
            assert "data.txt" not in file_paths
    
    def test_symlink_to_directory_is_skipped(self, tmp_path):
        """
        SECURITY TEST: Symlinks to directories should not cause traversal.
        
        A symlink to a directory (e.g., /etc) should not cause os.walk to
        traverse outside the repo.
        """
        # Create a symlink to a directory
        if os.path.exists("/etc"):
            etc_link = tmp_path / "etc_link"
            etc_link.symlink_to("/etc")
            
            files, total = _read_key_files(str(tmp_path), max_bytes=50000)
            
            # None of the files should have paths starting with etc_link/
            file_paths = [f["path"] for f in files]
            assert not any(p.startswith("etc_link/") for p in file_paths)
    
    def test_normal_files_still_work_after_symlink_fix(self, tmp_path):
        """
        REGRESSION TEST: Normal files should still be read correctly.
        
        The symlink protection should not break normal file reading.
        This test ensures the security fix doesn't prevent legitimate repos
        from being reviewed.
        """
        # Create normal files
        readme = tmp_path / "README.md"
        readme.write_text("# Normal Project\nThis is safe.")
        
        main = tmp_path / "main.py"
        main.write_text("def main():\n    pass")
        
        files, total = _read_key_files(str(tmp_path), max_bytes=50000)
        
        # Both normal files should be read successfully
        file_paths = [f["path"] for f in files]
        assert "README.md" in file_paths
        assert "main.py" in file_paths
        
        # Verify content is correct
        readme_content = next(f["content"] for f in files if f["path"] == "README.md")
        assert "Normal Project" in readme_content
    
    def test_git_clone_with_core_symlinks_false(self, tmp_path):
        """
        INTEGRATION TEST: Verify git clone command includes -c core.symlinks=false.
        
        This tests that the git clone command is constructed with the security
        flag that tells git to NOT create symlinks, even if they exist in the
        repository history. This is defense-in-depth: even if a malicious repo
        has symlinks committed, git won't create them on the runner filesystem.
        """
        with patch("stage_3_read_linked_repo.subprocess.run") as mock_run:
            with patch("stage_3_read_linked_repo.tempfile.mkdtemp", return_value=str(tmp_path)):
                with patch("stage_3_read_linked_repo.shutil.rmtree"):
                    with patch("stage_3_read_linked_repo._extract_file_tree", return_value=("", 0)):
                        with patch("stage_3_read_linked_repo._read_key_files", return_value=([], 0)):
                            mock_run.return_value = MagicMock(returncode=0, stderr="")
                            
                            read_linked_repository(
                                repo_url="https://github.com/test/repo",
                                commit_sha=None,
                                repo_visibility="public",
                            )
                            
                            # Verify git clone was called with -c core.symlinks=false
                            clone_call = mock_run.call_args_list[0]
                            cmd = clone_call[0][0]
                            
                            assert "-c" in cmd
                            assert "core.symlinks=false" in cmd
    
    @patch("stage_3_read_linked_repo.subprocess.run")
    @patch("stage_3_read_linked_repo.tempfile.mkdtemp")
    @patch("stage_3_read_linked_repo.shutil.rmtree")
    def test_full_integration_malicious_repo_blocked(self, mock_rmtree, mock_mkdtemp, mock_run, tmp_path):
        """
        FULL INTEGRATION TEST: Simulate a malicious repo with multiple attack vectors.
        
        This test creates a realistic attack scenario with multiple symlinks
        targeting different sensitive files, and verifies that ALL of them are
        blocked by the fix.
        """
        # Set up a fake cloned repo with attack vectors
        mock_mkdtemp.return_value = str(tmp_path)
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        
        # Create legitimate files
        (tmp_path / "README.md").write_text("# Malicious Repo\nLooks innocent!")
        (tmp_path / "main.py").write_text("print('hello')")
        
        # Create attack vectors (symlinks)
        if os.path.exists("/etc/passwd"):
            (tmp_path / "users.txt").symlink_to("/etc/passwd")
        
        if os.path.exists("/proc/self/environ"):
            (tmp_path / "config.json").symlink_to("/proc/self/environ")
        
        # Mock the internal functions to use the real implementations on our tmp_path
        with patch("stage_3_read_linked_repo._extract_file_tree", side_effect=lambda d: _extract_file_tree(d)):
            with patch("stage_3_read_linked_repo._read_key_files", side_effect=lambda d, m: _read_key_files(d, m)):
                result = read_linked_repository(
                    repo_url="https://github.com/attacker/evil-repo",
                    commit_sha=None,
                    repo_visibility="public",
                )
        
        # Verify the repo was "processed" successfully (we don't fail; we just skip bad files)
        assert result["available"] is True
        
        # Verify ONLY the legitimate files were read
        file_paths = [f["path"] for f in result["key_files"]]
        assert "README.md" in file_paths
        assert "main.py" in file_paths
        
        # Verify the attack vectors were blocked
        assert "users.txt" not in file_paths
        assert "config.json" not in file_paths
        
        # Verify no sensitive content leaked through
        all_content = " ".join(f["content"] for f in result["key_files"])
        assert "root:x:0:0" not in all_content  # /etc/passwd content
        # We can't easily test for env vars here since we're not in the runner context
