"""
Stage 3: Read Linked Repository — Pubroot

PURPOSE:
    When a submitter links a GitHub repository as supporting evidence for their
    article, this stage reads that repo to provide the LLM reviewer with code
    context. The reviewer can then assess code quality, check if the code matches
    the claims in the article, and verify reproducibility.
    
    This stage does NOT execute any code. It only reads file structure and content.
    This is a deliberate safety decision — we never run untrusted code. The review
    is "static analysis" in the sense that we read the code and ask the LLM to
    evaluate it, but we don't actually compile or execute anything.

CALLED BY:
    review_pipeline_main.py — passes the repo URL, optional commit SHA, and
    visibility setting from the parsed submission.

DEPENDS ON:
    - A public GitHub repo (for 'public' visibility submissions)
    - A GitHub App installation token (for 'private' visibility — DEFERRED)
    - The `git` CLI being available in the runner (GitHub Actions has it by default)
    - The `requests` library for GitHub API calls

DESIGN DECISIONS:
    - We clone the repo into a temp directory rather than using the GitHub API to
      read individual files. Cloning is faster for reading multiple files and gives
      us the full tree structure. It also works offline once cloned.
    - We limit total extracted content to 50KB to keep the review prompt manageable.
      The Gemini context window is 1M tokens, but we want to leave room for the
      article text, calibration examples, and novelty results.
    - We prioritize reading: README, main entry points (main.py, index.js, etc.),
      requirements/package files, and config files. These tell the LLM the most
      about the project with the least content.
    - Private repo support via GitHub App is deferred. When implemented, the
      review pipeline will use actions/create-github-app-token@v1 to get a
      short-lived installation token scoped to the submitter's repo.

COST:
    $0 — git clone of public repos is free. GitHub API reads are free within
    the 5,000 req/hr rate limit of the GITHUB_TOKEN.
"""

import os
import re
import subprocess
import tempfile
import shutil
from typing import Optional


def read_linked_repository(
    repo_url: Optional[str],
    commit_sha: Optional[str],
    repo_visibility: str,
    max_content_bytes: int = 50000
) -> dict:
    """
    Clone and read a submitter's linked GitHub repository.
    
    This is the ONLY public function in this file. It handles the full flow:
    clone the repo, check out the right commit, extract the file tree, and
    read key files up to the content limit.
    
    Args:
        repo_url: Full GitHub URL (e.g., "https://github.com/owner/repo").
                  None if no repo was provided (text-only submission).
        commit_sha: Optional specific commit to pin to. If None, uses HEAD.
                    This ensures we review the exact version the submitter intended.
        repo_visibility: One of 'public', 'private', 'no-repo'.
                        'private' support is deferred (returns a placeholder).
        max_content_bytes: Maximum total bytes of file content to extract.
                          Defaults to 50KB. This keeps the review prompt size
                          manageable while still giving the LLM enough context.
    
    Returns:
        dict with keys:
            - 'available' (bool): Whether repo content was successfully read
            - 'visibility' (str): 'public', 'private', or 'no-repo'
            - 'file_tree' (str): The full directory tree as a string
            - 'file_count' (int): Total number of files in the repo
            - 'key_files' (list[dict]): List of extracted files, each with:
                - 'path' (str): relative file path
                - 'content' (str): file content (truncated if necessary)
                - 'size_bytes' (int): original file size
                - 'truncated' (bool): whether content was cut short
            - 'total_content_bytes' (int): Total bytes of content extracted
            - 'badge_type' (str): 'verified_open', 'verified_private', or 'text_only'
            - 'errors' (list[str]): Any errors encountered
    """
    
    errors = []
    
    # -----------------------------------------------------------------------
    # CASE 1: No repo provided (text-only submission)
    # -----------------------------------------------------------------------
    # This is valid — many submissions (essays, debug logs without code) don't
    # have a supporting repo. They get a "text_only" badge which is lower trust
    # but still publishable if the text review passes.
    # -----------------------------------------------------------------------
    
    if not repo_url or repo_visibility == "no-repo":
        return {
            "available": False,
            "visibility": "no-repo",
            "file_tree": "",
            "file_count": 0,
            "key_files": [],
            "total_content_bytes": 0,
            "badge_type": "text_only",
            "errors": [],
        }
    
    # -----------------------------------------------------------------------
    # CASE 2: Private repo (deferred — requires GitHub App)
    # -----------------------------------------------------------------------
    # Private repo support requires registering a GitHub App, having the
    # submitter install it on their repo, and using a short-lived installation
    # token to clone. This is planned but not yet implemented.
    # For now, we note the private visibility and proceed without repo content.
    # The article still gets reviewed (text-only review) but with a different
    # badge: "verified_private" means the bot WILL verify once the feature ships.
    # -----------------------------------------------------------------------
    
    if repo_visibility == "private":
        return {
            "available": False,
            "visibility": "private",
            "file_tree": "",
            "file_count": 0,
            "key_files": [],
            "total_content_bytes": 0,
            "badge_type": "verified_private",
            "errors": ["Private repo review not yet supported. Article will be reviewed as text-only."],
        }
    
    # -----------------------------------------------------------------------
    # CASE 3: Public repo — clone and read
    # -----------------------------------------------------------------------
    
    # Validate the URL format before attempting to clone
    github_url_pattern = r"^https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$"
    match = re.match(github_url_pattern, repo_url)
    if not match:
        return {
            "available": False,
            "visibility": "public",
            "file_tree": "",
            "file_count": 0,
            "key_files": [],
            "total_content_bytes": 0,
            "badge_type": "text_only",
            "errors": [f"Invalid GitHub URL format: {repo_url}"],
        }
    
    owner = match.group(1)
    repo_name = match.group(2)
    
    # Clone into a temporary directory
    # We use --depth 1 for shallow clone (saves time and bandwidth) unless
    # a specific commit SHA is requested, in which case we need full history
    # to check out that exact commit.
    tmp_dir = tempfile.mkdtemp(prefix="review_repo_")
    
    try:
        # Clone the repository
        clone_cmd = ["git", "clone", "--quiet"]
        if not commit_sha:
            clone_cmd.extend(["--depth", "1"])
        clone_cmd.extend([repo_url, tmp_dir])
        
        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout for large repos
            cwd="/tmp"
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return {
                "available": False,
                "visibility": "public",
                "file_tree": "",
                "file_count": 0,
                "key_files": [],
                "total_content_bytes": 0,
                "badge_type": "text_only",
                "errors": [f"Failed to clone repo: {error_msg}"],
            }
        
        # If a specific commit SHA was requested, check it out
        if commit_sha:
            checkout_result = subprocess.run(
                ["git", "checkout", commit_sha],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmp_dir
            )
            if checkout_result.returncode != 0:
                errors.append(
                    f"Could not checkout commit {commit_sha}. "
                    f"Reviewing HEAD instead."
                )
        
        # ---------------------------------------------------------------
        # Extract the file tree
        # ---------------------------------------------------------------
        # We use `find` to list all files, excluding .git directory and
        # common non-essential directories (node_modules, __pycache__, etc.)
        # ---------------------------------------------------------------
        
        file_tree, file_count = _extract_file_tree(tmp_dir)
        
        # ---------------------------------------------------------------
        # Read key files up to the content limit
        # ---------------------------------------------------------------
        # Priority order for reading files (most informative first):
        # 1. README files (project overview)
        # 2. Dependency files (requirements.txt, package.json, Cargo.toml)
        # 3. Config files (.env.example, config.*, setup.*)
        # 4. Main entry points (main.py, index.js, app.py, etc.)
        # 5. Source files sorted by name (alphabetical)
        # ---------------------------------------------------------------
        
        key_files, total_bytes = _read_key_files(tmp_dir, max_content_bytes)
        
        return {
            "available": True,
            "visibility": "public",
            "file_tree": file_tree,
            "file_count": file_count,
            "key_files": key_files,
            "total_content_bytes": total_bytes,
            "badge_type": "verified_open",
            "errors": errors,
        }
    
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "visibility": "public",
            "file_tree": "",
            "file_count": 0,
            "key_files": [],
            "total_content_bytes": 0,
            "badge_type": "text_only",
            "errors": ["Repository clone timed out (>120 seconds). Repo may be too large."],
        }
    except Exception as e:
        return {
            "available": False,
            "visibility": "public",
            "file_tree": "",
            "file_count": 0,
            "key_files": [],
            "total_content_bytes": 0,
            "badge_type": "text_only",
            "errors": [f"Unexpected error reading repo: {str(e)}"],
        }
    finally:
        # Always clean up the temp directory to avoid filling the runner's disk
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# PRIVATE HELPER FUNCTIONS
# ---------------------------------------------------------------------------


def _extract_file_tree(repo_dir: str) -> tuple:
    """
    Generate a text representation of the repository's file tree.
    
    We exclude .git/, node_modules/, __pycache__/, .venv/, dist/, build/,
    and other common non-essential directories to focus on source code.
    
    Returns:
        tuple of (tree_string, file_count)
    """
    exclude_dirs = {
        ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
        "dist", "build", ".next", ".nuxt", ".cache", ".tox",
        "target", "vendor", ".gradle", ".idea", ".vscode",
    }
    
    exclude_extensions = {
        ".pyc", ".pyo", ".class", ".o", ".so", ".dylib", ".dll",
        ".exe", ".bin", ".dat", ".db", ".sqlite", ".lock",
    }
    
    all_files = []
    
    for root, dirs, files in os.walk(repo_dir):
        # Filter out excluded directories (modifies dirs in-place to prevent descent)
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for filename in sorted(files):
            # Skip hidden files (except important ones like .env.example)
            if filename.startswith(".") and filename not in {".env.example", ".gitignore", ".dockerignore"}:
                continue
            
            # Skip binary-ish extensions
            ext = os.path.splitext(filename)[1].lower()
            if ext in exclude_extensions:
                continue
            
            rel_path = os.path.relpath(os.path.join(root, filename), repo_dir)
            all_files.append(rel_path)
    
    # Build tree string (simple indented listing)
    tree_lines = []
    for path in sorted(all_files):
        depth = path.count(os.sep)
        indent = "  " * depth
        basename = os.path.basename(path)
        tree_lines.append(f"{indent}{basename}")
    
    tree_string = "\n".join(tree_lines[:200])  # Cap at 200 lines
    if len(all_files) > 200:
        tree_string += f"\n... and {len(all_files) - 200} more files"
    
    return tree_string, len(all_files)


def _read_key_files(repo_dir: str, max_bytes: int) -> tuple:
    """
    Read the most informative files from the repo up to the byte limit.
    
    Files are read in priority order: README first, then dependency files,
    then config files, then main entry points, then other source files.
    We stop reading once we hit the max_bytes limit.
    
    Returns:
        tuple of (list_of_file_dicts, total_bytes_read)
    """
    
    # Define priority patterns. Files matching earlier patterns are read first.
    # This ensures the LLM sees the most important context even if we hit the limit.
    priority_patterns = [
        # Priority 1: README files — project overview
        re.compile(r"^README(\.\w+)?$", re.IGNORECASE),
        # Priority 2: Dependency/package files — what the project needs
        re.compile(r"^(requirements\.txt|Pipfile|pyproject\.toml|package\.json|Cargo\.toml|go\.mod|Gemfile|pom\.xml)$"),
        # Priority 3: Config files — how the project is set up
        re.compile(r"^(\.env\.example|config\.\w+|setup\.\w+|Dockerfile|docker-compose\.\w+|Makefile)$"),
        # Priority 4: Main entry points — the actual code logic
        re.compile(r"^(main\.py|app\.py|index\.\w+|server\.\w+|cli\.py|__main__\.py)$"),
    ]
    
    # Collect all readable files with their priority
    files_with_priority = []
    
    exclude_dirs = {
        ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
        "dist", "build", ".next", ".cache", "target", "vendor",
    }
    
    text_extensions = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".rb", ".java",
        ".swift", ".kt", ".c", ".cpp", ".h", ".hpp", ".cs", ".sh", ".bash",
        ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf",
        ".md", ".txt", ".rst", ".html", ".css", ".scss", ".sql",
        ".r", ".R", ".jl", ".lua", ".php", ".pl", ".ex", ".exs",
        ".dockerfile", ".tf", ".hcl",
    }
    
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            # Include files with known text extensions or no extension (like Makefile, Dockerfile)
            if ext not in text_extensions and ext != "":
                continue
            
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, repo_dir)
            
            # Skip large files (>100KB individual) — they're probably generated or data
            try:
                file_size = os.path.getsize(full_path)
            except OSError:
                continue
            if file_size > 100000:
                continue
            
            # Determine priority (lower number = higher priority = read first)
            priority = 99  # Default: lowest priority
            for i, pattern in enumerate(priority_patterns):
                if pattern.match(filename):
                    priority = i
                    break
            
            files_with_priority.append((priority, rel_path, full_path, file_size))
    
    # Sort by priority (ascending), then by path for deterministic ordering
    files_with_priority.sort(key=lambda x: (x[0], x[1]))
    
    # Read files until we hit the byte limit
    key_files = []
    total_bytes = 0
    
    for priority, rel_path, full_path, file_size in files_with_priority:
        if total_bytes >= max_bytes:
            break
        
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        
        # Truncate if adding this file would exceed the limit
        remaining = max_bytes - total_bytes
        truncated = False
        if len(content.encode("utf-8")) > remaining:
            # Truncate at a line boundary to avoid cutting mid-line
            content_bytes = content.encode("utf-8")[:remaining]
            content = content_bytes.decode("utf-8", errors="replace")
            # Find the last newline and cut there
            last_newline = content.rfind("\n")
            if last_newline > 0:
                content = content[:last_newline]
            truncated = True
        
        content_size = len(content.encode("utf-8"))
        total_bytes += content_size
        
        key_files.append({
            "path": rel_path,
            "content": content,
            "size_bytes": file_size,
            "truncated": truncated,
        })
    
    return key_files, total_bytes
