# Pubroot - Review Agent Package
# 
# This package contains the 6-stage review pipeline that processes
# submissions from GitHub Issues. Each stage is in its own file
# following the one-function-per-file architecture pattern.
#
# The pipeline is orchestrated by review_pipeline_main.py and runs
# inside a GitHub Actions Ubuntu runner. It reads from the GitHub
# event payload (issue body), calls external APIs (Gemini, arXiv,
# Semantic Scholar), and writes back to GitHub (comments, PRs, labels).
#
# Stage flow:
#   1. Parse & Filter -> 2. Novelty Check -> 3. Read Linked Repo
#   -> 4. Build Review Prompt -> 5. Gemini Grounded Review
#   -> 6. Post Review & Decide
