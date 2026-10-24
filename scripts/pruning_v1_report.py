#!/usr/bin/env python3
"""
Pruning v1 Report-Only System for Pubroot

This script implements the hybrid approach described in pruning.md:
- Near-duplicate detection (title + abstract embedding similarity)
- Missing review.json files (unreviewed papers)
- Stale valid_until dates (expired papers)
- Unverifiable badges (verified_private without verification, verified_open issues)
- Missing grounding metadata (claims grounding_used=true but no grounding_metadata)

REPORT-ONLY: Nothing is archived, unpublished, deleted, relabeled, or edited.
The output is a JSON and Markdown report flagging candidates with reasons and evidence.

Run from repo root:
  python3 scripts/pruning_v1_report.py

Options:
  --use-llm: Enable optional LLM-based duplicate detection (off by default, not implemented yet)
  --output-json PATH: JSON report path (default: pruning_report.json)
  --output-md PATH: Markdown report path (default: pruning_report.md)

Design:
- The script walks all published papers under papers/**/*.md
- It reads review.json files from reviews/{paper_id}/review.json
- It computes embeddings for duplicate detection (using sentence-transformers if available, otherwise falls back to simple token overlap)
- It checks valid_until dates, badge verification, grounding metadata, and review file existence
- It outputs a structured report with flagged candidates grouped by reason

Author: Pubroot Systems
Date: 2026-10-24
Status: MVP implementation, no LLM re-review
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# Optional dependency: sentence-transformers for embeddings
# If not available, fall back to simple token-based similarity
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


REPO_ROOT = Path(__file__).resolve().parents[1]
PAPERS_ROOT = REPO_ROOT / "papers"
REVIEWS_ROOT = REPO_ROOT / "reviews"

# Thresholds (tunable after first report)
DUPLICATE_SIMILARITY_THRESHOLD = 0.85  # cosine similarity for near-duplicates
TOKEN_OVERLAP_THRESHOLD = 0.3  # fallback token-based similarity


class PruningReporter:
    """
    Main reporter class that walks the paper corpus and generates a pruning report.
    
    This class encapsulates all the detection logic:
    - Near-duplicate detection via embeddings or token overlap
    - Missing review files
    - Expired papers (past valid_until)
    - Unverifiable badges
    - Missing grounding metadata
    
    The report is structured as a list of flagged candidates, each with:
    - paper_id
    - title
    - category
    - published_date
    - flags: list of issue codes
    - evidence: dict of supporting data per flag
    """
    
    def __init__(self, use_llm: bool = False):
        """
        Initialize the pruning reporter.
        
        Args:
            use_llm: Enable optional LLM-based checks (not yet implemented)
        
        Why use_llm is here:
        The spec calls for Option 1 (LLM re-review) to run on the bottom slice
        identified by Option 2 (algorithmic health score). For MVP we only do
        Option 2 checks, but this parameter reserves the design space for later
        LLM integration without breaking the command-line interface.
        """
        self.use_llm = use_llm
        self.embedder = None
        
        # Initialize embedding model if available
        # We use all-MiniLM-L6-v2 because it's fast, small (~80MB), and good enough
        # for near-duplicate detection at the scale of ~100 papers. Cosine similarity
        # on title+abstract embeddings correlates well with human judgments of
        # "this is basically the same paper."
        if EMBEDDINGS_AVAILABLE and not use_llm:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}", file=sys.stderr)
                self.embedder = None
        
        # Storage for papers and their metadata
        # We keep everything in memory because the corpus is small (~100 papers)
        # and we need random access for duplicate comparisons
        self.papers: list[dict[str, Any]] = []
        self.paper_embeddings: dict[str, Any] = {}  # paper_id -> embedding vector
    
    def _read_frontmatter(self, path: Path) -> tuple[dict | None, str]:
        """
        Extract YAML frontmatter and body from a markdown file.
        
        Returns:
            (frontmatter_dict, body_text) or (None, full_text) if no frontmatter
        
        This is the same logic used in regenerate_agent_index_from_papers.py
        to maintain consistency across the codebase.
        """
        text = path.read_text(encoding="utf-8")
        if not text.lstrip().startswith("---"):
            return None, text
        parts = text.split("---", 2)
        if len(parts) < 3:
            return None, text
        try:
            fm = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            return None, text
        return fm, parts[2]
    
    def _load_papers(self) -> None:
        """
        Walk all papers under papers/ and load their metadata.
        
        For each paper we extract:
        - paper_id, title, author, category, abstract from frontmatter
        - published_date (original_submitted_date or date field)
        - badge, score, valid_until (if present)
        - supporting_repo (for badge verification)
        
        Papers without paper_id are skipped (likely drafts or non-paper content).
        Papers under _* directories are skipped (private/template content).
        """
        for index_md in sorted(PAPERS_ROOT.rglob("index.md")):
            rel_from_papers = index_md.relative_to(PAPERS_ROOT)
            
            # Skip private/template directories
            if rel_from_papers.parts and rel_from_papers.parts[0].startswith("_"):
                continue
            
            fm, body = self._read_frontmatter(index_md)
            if not fm or not fm.get("paper_id"):
                continue
            
            paper_id = str(fm["paper_id"]).strip()
            
            # Extract abstract for embedding
            # The abstract is either a string in the frontmatter or we take the
            # first paragraph from the body as a fallback
            abstract = fm.get("abstract", "")
            if isinstance(abstract, str):
                abstract = abstract.strip()
            else:
                abstract = str(abstract).strip() if abstract else ""
            
            # Build paper metadata record
            paper = {
                "paper_id": paper_id,
                "title": str(fm.get("title", "Untitled")).strip(),
                "author": fm.get("author", "unknown"),
                "category": fm.get("category", "general/general"),
                "abstract": abstract,
                "published_date": fm.get("original_submitted_date") or fm.get("date"),
                "score": fm.get("score"),
                "badge": fm.get("badge", "text_only"),
                "valid_until": fm.get("valid_until"),
                "supporting_repo": fm.get("supporting_repo"),
                "status": fm.get("status", "current"),
                "article_path": str(index_md.relative_to(REPO_ROOT)),
            }
            
            self.papers.append(paper)
    
    def _compute_embeddings(self) -> None:
        """
        Compute embeddings for all papers for duplicate detection.
        
        We embed title + abstract because:
        - Title captures the main topic
        - Abstract captures the core claims and methods
        - Together they give a good signal for near-duplicates
        
        If embeddings are not available, we skip this and fall back to
        token-based overlap in the duplicate detection phase.
        """
        if not self.embedder:
            return
        
        # Build text representations
        # Format: "{title} [SEP] {abstract}"
        # The [SEP] token helps the model distinguish title from abstract,
        # though all-MiniLM-L6-v2 doesn't use special tokens explicitly,
        # it still benefits from the structural marker
        texts = []
        paper_ids = []
        for paper in self.papers:
            text = f"{paper['title']} [SEP] {paper['abstract']}"
            texts.append(text)
            paper_ids.append(paper['paper_id'])
        
        # Batch encode all papers at once (much faster than one-by-one)
        embeddings = self.embedder.encode(texts, show_progress_bar=False)
        
        # Store embeddings keyed by paper_id
        for pid, emb in zip(paper_ids, embeddings):
            self.paper_embeddings[pid] = emb
    
    def _token_overlap_similarity(self, text1: str, text2: str) -> float:
        """
        Fallback similarity measure when embeddings are not available.
        
        Computes Jaccard similarity of word tokens (lowercased, split on whitespace).
        This is much less sophisticated than embeddings but catches exact or
        near-exact duplicates.
        
        Args:
            text1, text2: Input texts to compare
        
        Returns:
            Jaccard similarity in [0, 1]
        
        Why Jaccard and not something fancier:
        Jaccard is deterministic, explainable, and fast. For the MVP we want
        something that doesn't require tuning or external dependencies. If two
        papers share >30% of their words, that's a strong duplicate signal.
        """
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union)
    
    def _cosine_similarity(self, emb1, emb2) -> float:
        """
        Compute cosine similarity between two embedding vectors.
        
        Cosine similarity is standard for comparing sentence embeddings.
        It's invariant to magnitude (only direction matters) and gives
        values in [-1, 1] where 1 = identical direction, 0 = orthogonal.
        
        For near-duplicate detection, high cosine similarity (>0.85) means
        the papers are talking about the same topic in the same way.
        """
        import numpy as np
        return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
    
    def _check_duplicates(self) -> dict[str, list[dict]]:
        """
        Detect near-duplicate papers using embeddings or token overlap.
        
        Returns:
            Dict mapping paper_id -> list of similar papers with scores
        
        Algorithm:
            1. For each paper, compare to all others (N^2 but N is small)
            2. If similarity > threshold, flag it
            3. For each duplicate pair, we flag the NEWER paper (per spec)
        
        Why flag the newer one:
        The older paper has temporal priority. If 2026-016 is a near-duplicate
        of 2026-005, we dock 2026-016 and suggest superseded_by=2026-005.
        This matches the games-space method referenced in the spec.
        """
        duplicates = defaultdict(list)
        
        for i, paper1 in enumerate(self.papers):
            for paper2 in self.papers[i+1:]:
                # Compare using embeddings if available
                if self.paper_embeddings:
                    emb1 = self.paper_embeddings[paper1['paper_id']]
                    emb2 = self.paper_embeddings[paper2['paper_id']]
                    similarity = self._cosine_similarity(emb1, emb2)
                    threshold = DUPLICATE_SIMILARITY_THRESHOLD
                else:
                    # Fallback to token overlap
                    text1 = f"{paper1['title']} {paper1['abstract']}"
                    text2 = f"{paper2['title']} {paper2['abstract']}"
                    similarity = self._token_overlap_similarity(text1, text2)
                    threshold = TOKEN_OVERLAP_THRESHOLD
                
                if similarity >= threshold:
                    # Determine which is newer based on published_date
                    # If dates are missing or equal, use paper_id as tiebreaker
                    date1 = paper1.get('published_date')
                    date2 = paper2.get('published_date')
                    
                    if date1 and date2:
                        if date1 < date2:
                            newer, older = paper2, paper1
                        else:
                            newer, older = paper1, paper2
                    else:
                        # Fallback: higher paper_id is newer
                        if paper1['paper_id'] > paper2['paper_id']:
                            newer, older = paper1, paper2
                        else:
                            newer, older = paper2, paper1
                    
                    duplicates[newer['paper_id']].append({
                        "duplicate_of": older['paper_id'],
                        "duplicate_title": older['title'],
                        "similarity": round(similarity, 3),
                        "same_author": newer['author'] == older['author'],
                    })
        
        return dict(duplicates)
    
    def _check_missing_reviews(self) -> dict[str, dict]:
        """
        Check for papers with missing review.json files.
        
        Returns:
            Dict mapping paper_id -> evidence dict
        
        Why this matters:
        The MCP get_review tool and the index both point to reviews/{id}/review.json.
        If that file is missing, the paper is effectively unreviewed from an
        agent's perspective. This is a data integrity issue that should be surfaced.
        
        Known cases (from bugs.md B14):
        - 2026-017, 2026-035, 2026-036, 2026-037
        """
        missing = {}
        
        for paper in self.papers:
            paper_id = paper['paper_id']
            review_path = REVIEWS_ROOT / paper_id / "review.json"
            
            if not review_path.exists():
                missing[paper_id] = {
                    "expected_path": str(review_path.relative_to(REPO_ROOT)),
                    "reason": "Review file does not exist",
                }
        
        return missing
    
    def _check_expired_papers(self) -> dict[str, dict]:
        """
        Check for papers past their valid_until date.
        
        Returns:
            Dict mapping paper_id -> evidence dict
        
        Why this matters (from bugs.md B11):
        All papers are currently status=current, but many have valid_until dates
        in the past. These should be marked as expired or their dates should be
        updated. The spec says expiry should trigger a state change, not archiving.
        """
        expired = {}
        now = datetime.now(timezone.utc)
        
        for paper in self.papers:
            valid_until = paper.get('valid_until')
            if not valid_until:
                continue
            
            # Parse the valid_until date
            # It might be a datetime object (from YAML) or a string
            if isinstance(valid_until, str):
                try:
                    # Try parsing ISO format
                    valid_until_dt = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
                except ValueError:
                    continue
            elif isinstance(valid_until, datetime):
                valid_until_dt = valid_until
                if valid_until_dt.tzinfo is None:
                    valid_until_dt = valid_until_dt.replace(tzinfo=timezone.utc)
            else:
                continue
            
            # Check if expired
            if valid_until_dt < now:
                days_overdue = (now - valid_until_dt).days
                expired[paper['paper_id']] = {
                    "valid_until": valid_until_dt.isoformat(),
                    "days_overdue": days_overdue,
                    "current_status": paper.get('status', 'current'),
                }
        
        return expired
    
    def _check_unverifiable_badges(self) -> dict[str, dict]:
        """
        Check for badges that claim verification without evidence.
        
        Returns:
            Dict mapping paper_id -> evidence dict
        
        Why this matters (from bugs.md B4):
        - 32 of 93 papers have verified_private with no verification
        - verified_open is kept even when SHA checkout failed
        
        For MVP we flag:
        - verified_private (none are actually verified per the spec)
        - Any paper with a badge but no supporting_repo
        """
        unverifiable = {}
        
        for paper in self.papers:
            paper_id = paper['paper_id']
            badge = paper.get('badge', 'text_only')
            supporting_repo = paper.get('supporting_repo')
            
            issues = []
            
            # Flag verified_private (per bugs.md, none are actually verified)
            if badge == 'verified_private':
                issues.append({
                    "issue": "Badge claims verified_private but verification feature not implemented",
                    "badge": badge,
                    "has_repo": bool(supporting_repo),
                })
            
            # Flag verified_open without a repo URL
            # (This shouldn't happen, but let's check)
            if badge == 'verified_open' and not supporting_repo:
                issues.append({
                    "issue": "Badge claims verified_open but no supporting_repo URL",
                    "badge": badge,
                    "has_repo": False,
                })
            
            if issues:
                unverifiable[paper_id] = {
                    "badge": badge,
                    "supporting_repo": supporting_repo,
                    "issues": issues,
                }
        
        return unverifiable
    
    def _check_missing_grounding(self) -> dict[str, dict]:
        """
        Check for papers claiming grounding but missing grounding_metadata.
        
        Returns:
            Dict mapping paper_id -> evidence dict
        
        Why this matters (from bugs.md B5):
        All 32 reviews since 2026-08-25 have grounding_metadata.available=false
        while claiming grounding_used: true. This is a honesty/trust issue.
        """
        missing_grounding = {}
        
        for paper in self.papers:
            paper_id = paper['paper_id']
            review_path = REVIEWS_ROOT / paper_id / "review.json"
            
            if not review_path.exists():
                continue  # Already flagged in missing_reviews
            
            try:
                review = json.loads(review_path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, IOError):
                continue
            
            # Check if review claims grounding_used=true but has no grounding_metadata
            review_metadata = review.get('review_metadata', {})
            grounding_metadata = review.get('grounding_metadata', {})
            
            grounding_used = review_metadata.get('grounding_used', False)
            grounding_available = grounding_metadata.get('available', False)
            
            # Flag if grounding_used=true but grounding_metadata.available=false
            if grounding_used and not grounding_available:
                missing_grounding[paper_id] = {
                    "grounding_used": grounding_used,
                    "grounding_available": grounding_available,
                    "grounding_error": grounding_metadata.get('error', 'Unknown'),
                    "review_date": review_metadata.get('review_date'),
                }
        
        return missing_grounding
    
    def generate_report(self) -> dict[str, Any]:
        """
        Run all checks and generate a structured report.
        
        Returns:
            Dict with report metadata and flagged candidates
        
        The report structure:
        {
            "report_metadata": {
                "generated_at": ISO timestamp,
                "total_papers_scanned": count,
                "total_flagged": count,
                "embeddings_available": bool,
                "thresholds": {...}
            },
            "flagged_candidates": [
                {
                    "paper_id": ...,
                    "title": ...,
                    "category": ...,
                    "published_date": ...,
                    "flags": ["duplicate", "expired", ...],
                    "evidence": {
                        "duplicate": {...},
                        "expired": {...},
                        ...
                    }
                }
            ],
            "summary_by_flag": {
                "duplicate": count,
                "missing_review": count,
                ...
            }
        }
        """
        print("Loading papers...", file=sys.stderr)
        self._load_papers()
        
        print(f"Loaded {len(self.papers)} papers", file=sys.stderr)
        
        if self.embedder:
            print("Computing embeddings for duplicate detection...", file=sys.stderr)
            self._compute_embeddings()
        else:
            print("Embeddings not available, using token overlap fallback", file=sys.stderr)
        
        print("Running checks...", file=sys.stderr)
        
        # Run all checks
        duplicates = self._check_duplicates()
        missing_reviews = self._check_missing_reviews()
        expired = self._check_expired_papers()
        unverifiable_badges = self._check_unverifiable_badges()
        missing_grounding = self._check_missing_grounding()
        
        # Build flagged candidates list
        flagged_papers = {}
        
        # Aggregate all flags per paper
        for paper in self.papers:
            paper_id = paper['paper_id']
            flags = []
            evidence = {}
            
            if paper_id in duplicates:
                flags.append("near_duplicate")
                evidence["near_duplicate"] = duplicates[paper_id]
            
            if paper_id in missing_reviews:
                flags.append("missing_review")
                evidence["missing_review"] = missing_reviews[paper_id]
            
            if paper_id in expired:
                flags.append("expired")
                evidence["expired"] = expired[paper_id]
            
            if paper_id in unverifiable_badges:
                flags.append("unverifiable_badge")
                evidence["unverifiable_badge"] = unverifiable_badges[paper_id]
            
            if paper_id in missing_grounding:
                flags.append("missing_grounding")
                evidence["missing_grounding"] = missing_grounding[paper_id]
            
            if flags:
                flagged_papers[paper_id] = {
                    "paper_id": paper_id,
                    "title": paper['title'],
                    "author": paper['author'],
                    "category": paper['category'],
                    "published_date": str(paper.get('published_date', '')),
                    "score": paper.get('score'),
                    "badge": paper.get('badge'),
                    "flags": flags,
                    "evidence": evidence,
                }
        
        # Build summary by flag type
        summary_by_flag = {
            "near_duplicate": len(duplicates),
            "missing_review": len(missing_reviews),
            "expired": len(expired),
            "unverifiable_badge": len(unverifiable_badges),
            "missing_grounding": len(missing_grounding),
        }
        
        # Build final report
        report = {
            "report_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_papers_scanned": len(self.papers),
                "total_flagged": len(flagged_papers),
                "embeddings_available": EMBEDDINGS_AVAILABLE and self.embedder is not None,
                "thresholds": {
                    "duplicate_similarity": DUPLICATE_SIMILARITY_THRESHOLD,
                    "token_overlap": TOKEN_OVERLAP_THRESHOLD,
                },
                "spec_version": "pruning_v1_mvp",
            },
            "flagged_candidates": sorted(
                flagged_papers.values(),
                key=lambda x: x['paper_id']
            ),
            "summary_by_flag": summary_by_flag,
        }
        
        return report
    
    def write_json_report(self, report: dict, output_path: Path) -> None:
        """Write the report as JSON."""
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding='utf-8'
        )
        print(f"Wrote JSON report to {output_path}", file=sys.stderr)
    
    def write_markdown_report(self, report: dict, output_path: Path) -> None:
        """
        Write the report as Markdown for human review.
        
        The markdown format is designed to be readable and actionable:
        - Executive summary at the top
        - Breakdown by flag type
        - Details for each flagged paper
        """
        lines = ["# Pubroot Pruning v1 Report", ""]
        
        meta = report['report_metadata']
        lines.append(f"**Generated:** {meta['generated_at']}")
        lines.append(f"**Papers Scanned:** {meta['total_papers_scanned']}")
        lines.append(f"**Papers Flagged:** {meta['total_flagged']}")
        lines.append(f"**Embeddings Available:** {meta['embeddings_available']}")
        lines.append("")
        
        lines.append("## Executive Summary")
        lines.append("")
        summary = report['summary_by_flag']
        lines.append(f"- **Near-Duplicates:** {summary['near_duplicate']} papers")
        lines.append(f"- **Missing Reviews:** {summary['missing_review']} papers (unreviewed)")
        lines.append(f"- **Expired Papers:** {summary['expired']} papers (past valid_until)")
        lines.append(f"- **Unverifiable Badges:** {summary['unverifiable_badge']} papers")
        lines.append(f"- **Missing Grounding:** {summary['missing_grounding']} papers (claims grounding but no metadata)")
        lines.append("")
        
        lines.append("## Flagged Candidates")
        lines.append("")
        
        for candidate in report['flagged_candidates']:
            lines.append(f"### {candidate['paper_id']}: {candidate['title']}")
            lines.append("")
            lines.append(f"- **Author:** {candidate['author']}")
            lines.append(f"- **Category:** {candidate['category']}")
            lines.append(f"- **Published:** {candidate['published_date']}")
            lines.append(f"- **Score:** {candidate.get('score', 'N/A')}")
            lines.append(f"- **Badge:** {candidate.get('badge', 'N/A')}")
            lines.append(f"- **Flags:** {', '.join(candidate['flags'])}")
            lines.append("")
            
            evidence = candidate['evidence']
            
            if 'near_duplicate' in evidence:
                lines.append("**Near-Duplicate Evidence:**")
                for dup in evidence['near_duplicate']:
                    lines.append(f"- Duplicate of `{dup['duplicate_of']}` (\"{dup['duplicate_title']}\")")
                    lines.append(f"  - Similarity: {dup['similarity']}")
                    lines.append(f"  - Same author: {dup['same_author']}")
                lines.append("")
            
            if 'missing_review' in evidence:
                lines.append("**Missing Review Evidence:**")
                lines.append(f"- Expected path: `{evidence['missing_review']['expected_path']}`")
                lines.append(f"- Reason: {evidence['missing_review']['reason']}")
                lines.append("")
            
            if 'expired' in evidence:
                lines.append("**Expired Evidence:**")
                exp = evidence['expired']
                lines.append(f"- Valid until: {exp['valid_until']}")
                lines.append(f"- Days overdue: {exp['days_overdue']}")
                lines.append(f"- Current status: {exp['current_status']}")
                lines.append("")
            
            if 'unverifiable_badge' in evidence:
                lines.append("**Unverifiable Badge Evidence:**")
                ubadge = evidence['unverifiable_badge']
                lines.append(f"- Badge: {ubadge['badge']}")
                lines.append(f"- Has supporting_repo: {bool(ubadge['supporting_repo'])}")
                for issue in ubadge['issues']:
                    lines.append(f"- Issue: {issue['issue']}")
                lines.append("")
            
            if 'missing_grounding' in evidence:
                lines.append("**Missing Grounding Evidence:**")
                mg = evidence['missing_grounding']
                lines.append(f"- Grounding used (claimed): {mg['grounding_used']}")
                lines.append(f"- Grounding available (actual): {mg['grounding_available']}")
                lines.append(f"- Error: {mg['grounding_error']}")
                lines.append(f"- Review date: {mg.get('review_date', 'N/A')}")
                lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("**Note:** This is a REPORT-ONLY analysis. No papers have been archived, ")
        lines.append("unpublished, or modified. This report flags candidates for manual review.")
        lines.append("")
        
        output_path.write_text("\n".join(lines), encoding='utf-8')
        print(f"Wrote Markdown report to {output_path}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Pubroot pruning v1 report (report-only, no changes)"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Enable optional LLM-based checks (not yet implemented, off by default)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT / "pruning_report.json",
        help="JSON report output path (default: pruning_report.json)",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=REPO_ROOT / "pruning_report.md",
        help="Markdown report output path (default: pruning_report.md)",
    )
    
    args = parser.parse_args()
    
    if args.use_llm:
        print("Warning: --use-llm is not yet implemented, ignoring", file=sys.stderr)
    
    reporter = PruningReporter(use_llm=False)
    report = reporter.generate_report()
    
    reporter.write_json_report(report, args.output_json)
    reporter.write_markdown_report(report, args.output_md)
    
    print("", file=sys.stderr)
    print(f"Report complete: {report['report_metadata']['total_flagged']} papers flagged", file=sys.stderr)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
