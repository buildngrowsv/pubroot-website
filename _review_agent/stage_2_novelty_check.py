"""
Stage 2: Novelty Check — Pubroot

PURPOSE:
    Search academic databases and the journal's own index to find existing work
    related to the submission. This serves two critical purposes:
    
    1. NOVELTY ASSESSMENT: Is the submission covering something already well-documented?
       If arXiv has 50 papers on this exact topic, the novelty score should be lower.
    
    2. SUPERSESSION DETECTION: Does the submission update or replace an existing article
       in our journal? If someone submits "GPT-5.4 Voice Benchmark" and we already have
       "GPT-5.3 Voice Benchmark", that's a supersession candidate.
    
    The results from this stage are injected into the Gemini review prompt (Stage 4)
    so the LLM can assess novelty in context and compare against existing literature.

CALLED BY:
    review_pipeline_main.py — passes the parsed submission title and abstract.

EXTERNAL APIS USED:
    - arXiv API (free, no key required): Searches 2.4M+ preprints in CS, physics, math, bio
    - Semantic Scholar API (free, optional key): Searches 231M+ papers across all fields
    - Internal agent-index.json: Our own published articles

COST:
    $0 — All three APIs are completely free. arXiv has no daily limit (just be polite,
    ~1 req/sec). Semantic Scholar allows 100K req/day with free API key.

DESIGN DECISIONS:
    - We search ALL THREE sources because they have different strengths:
      arXiv = CS preprints, S2 = broader published work with citations, 
      internal = our own journal's articles for supersession detection
    - We grab top 5 results from each to keep the prompt context manageable
    - We use simple keyword queries (not embeddings) in Phase 1. Phase 2 will
      add semantic search via all-MiniLM-L6-v2 embeddings when the corpus grows.
    - arXiv API returns XML which we parse manually (no dependency on feedparser)
      to keep the dependency list small.
    - We handle API failures gracefully — a failed novelty check should NOT block
      the review. The LLM can still review without novelty context.
"""

import json
import os
import re
import requests
import xml.etree.ElementTree as ET
from typing import Optional


def check_novelty(
    title: str,
    abstract: str,
    category: str,
    repo_root: str,
    s2_api_key: Optional[str] = None
) -> dict:
    """
    Search academic databases and internal index for work related to the submission.
    
    This is the ONLY public function in this file. It orchestrates searches across
    arXiv, Semantic Scholar, and the journal's own agent-index.json, then returns
    a combined result that Stage 4 (Build Review Prompt) will inject into the
    LLM review prompt.
    
    Args:
        title: The article title from the submission
        abstract: The article abstract from the submission
        category: The two-level "journal/topic" slug (e.g., 'ai/llm-benchmarks')
                  for context. Used by the internal index search for supersession
                  detection — papers in the same topic are the strongest candidates.
        repo_root: Path to repo root (to read agent-index.json)
        s2_api_key: Optional Semantic Scholar API key for higher rate limits.
                    The API works without a key but has lower rate limits.
    
    Returns:
        dict with keys:
            - 'arxiv_results' (list[dict]): Related papers from arXiv
            - 's2_results' (list[dict]): Related papers from Semantic Scholar
            - 'internal_results' (list[dict]): Related papers from our journal
            - 'potential_supersession' (dict or None): If the submission appears
              to update an existing internal paper
            - 'total_related' (int): Total number of related works found
            - 'errors' (list[str]): Any API errors encountered (non-blocking)
    """
    
    errors = []
    
    # Build a search query from the title and key abstract terms
    # We combine title + first few meaningful words of the abstract
    # to create a focused search query that captures the core topic
    search_query = _build_search_query(title, abstract)
    
    # -----------------------------------------------------------------------
    # SEARCH 1: arXiv API (free, no key required)
    # -----------------------------------------------------------------------
    # arXiv covers CS, physics, math, bio, econ, stats — perfect for technical
    # submissions. Returns title, abstract, authors, categories, date, PDF URL.
    # We search for related preprints to assess if this topic is already covered.
    # -----------------------------------------------------------------------
    
    arxiv_results = []
    try:
        arxiv_results = _search_arxiv(search_query, max_results=5)
    except Exception as e:
        errors.append(f"arXiv search failed: {str(e)}")
    
    # -----------------------------------------------------------------------
    # SEARCH 2: Semantic Scholar API (free, optional key)
    # -----------------------------------------------------------------------
    # S2 covers 231M+ papers across ALL disciplines (not just arXiv).
    # Returns citation counts, TL;DR summaries, and cross-references.
    # High citation count on related work = well-established topic = higher
    # bar for novelty in the submission.
    # -----------------------------------------------------------------------
    
    s2_results = []
    try:
        s2_results = _search_semantic_scholar(
            search_query, max_results=5, api_key=s2_api_key
        )
    except Exception as e:
        errors.append(f"Semantic Scholar search failed: {str(e)}")
    
    # -----------------------------------------------------------------------
    # SEARCH 3: Internal journal index (agent-index.json)
    # -----------------------------------------------------------------------
    # Search our own published articles. This is critical for:
    # - Supersession detection: "Is this an update to an existing paper?"
    # - Duplicate detection: "Did someone already submit this?"
    # - Topic freshness: "When was the last article on this topic?"
    # -----------------------------------------------------------------------
    
    internal_results = []
    potential_supersession = None
    try:
        internal_results, potential_supersession = _search_internal_index(
            search_query, title, category, repo_root
        )
    except Exception as e:
        errors.append(f"Internal index search failed: {str(e)}")
    
    # -----------------------------------------------------------------------
    # COMBINE RESULTS
    # -----------------------------------------------------------------------
    
    total_related = len(arxiv_results) + len(s2_results) + len(internal_results)
    
    return {
        "arxiv_results": arxiv_results,
        "s2_results": s2_results,
        "internal_results": internal_results,
        "potential_supersession": potential_supersession,
        "total_related": total_related,
        "search_query": search_query,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# PRIVATE HELPER FUNCTIONS
# ---------------------------------------------------------------------------


def _build_search_query(title: str, abstract: str) -> str:
    """
    Build a focused search query from the title and abstract.
    
    We take the full title and add the first ~50 words of the abstract,
    stripping Markdown formatting and common stop words. The goal is a
    query that captures the core topic without being too broad or too narrow.
    """
    # Clean Markdown formatting from the text
    clean_title = re.sub(r"[#*_`\[\]\(\)]", "", title).strip()
    
    # Take first ~50 words of abstract for additional context
    abstract_words = re.sub(r"[#*_`\[\]\(\)]", "", abstract).split()[:50]
    abstract_snippet = " ".join(abstract_words)
    
    # Combine: title is primary, abstract adds context
    query = f"{clean_title} {abstract_snippet}"
    
    # Limit total length to prevent overly long API queries
    if len(query) > 500:
        query = query[:500]
    
    return query


def _search_arxiv(query: str, max_results: int = 5) -> list:
    """
    Search the arXiv API for related papers.
    
    The arXiv API is free, requires no authentication, and has no strict daily
    limit. It returns XML (Atom format). We parse it manually to avoid adding
    the feedparser dependency.
    
    The API docs recommend limiting to 1 request per second. Since we only
    make 1 request per submission, this is never an issue.
    
    API docs: https://arxiv.org/help/api
    """
    # URL-encode the query. arXiv search supports full text search across
    # title, abstract, and content via the "all:" prefix.
    encoded_query = requests.utils.quote(query[:300])  # arXiv limits query length
    
    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query=all:{encoded_query}"
        f"&max_results={max_results}"
        f"&sortBy=relevance"
        f"&sortOrder=descending"
    )
    
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    # Parse the Atom XML response
    root = ET.fromstring(response.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    
    results = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        published_el = entry.find("atom:published", ns)
        
        # Get the arXiv ID from the entry id URL
        id_el = entry.find("atom:id", ns)
        arxiv_id = ""
        if id_el is not None and id_el.text:
            # ID format: http://arxiv.org/abs/2501.12345v1
            arxiv_id = id_el.text.split("/abs/")[-1] if "/abs/" in id_el.text else id_el.text
        
        # Get authors
        authors = []
        for author_el in entry.findall("atom:author", ns):
            name_el = author_el.find("atom:name", ns)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())
        
        result = {
            "source": "arxiv",
            "id": arxiv_id,
            "title": title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else "",
            "abstract": (summary_el.text.strip().replace("\n", " ")[:500] 
                        if summary_el is not None and summary_el.text else ""),
            "authors": authors[:5],  # Limit to first 5 authors
            "published": published_el.text[:10] if published_el is not None and published_el.text else "",
            "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
        }
        results.append(result)
    
    return results


def _search_semantic_scholar(
    query: str, 
    max_results: int = 5,
    api_key: Optional[str] = None
) -> list:
    """
    Search the Semantic Scholar API for related papers.
    
    S2 covers 231M+ papers across ALL academic disciplines. It's broader than
    arXiv and includes journal publications, conference proceedings, and more.
    It also provides citation counts and TL;DR summaries, which are useful
    for novelty assessment.
    
    Free tier: 100 requests/minute without key, 100K/day with free key.
    
    API docs: https://api.semanticscholar.org/
    """
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    params = {
        "query": query[:300],  # S2 has query length limits
        "limit": max_results,
        "fields": "title,abstract,citationCount,year,url,tldr",
    }
    
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    papers = data.get("data", [])
    
    results = []
    for paper in papers:
        tldr_text = ""
        tldr = paper.get("tldr")
        if tldr and isinstance(tldr, dict):
            tldr_text = tldr.get("text", "")
        
        result = {
            "source": "semantic_scholar",
            "id": paper.get("paperId", ""),
            "title": paper.get("title", ""),
            "abstract": (paper.get("abstract", "") or "")[:500],
            "citation_count": paper.get("citationCount", 0),
            "year": paper.get("year"),
            "url": paper.get("url", ""),
            "tldr": tldr_text,
        }
        results.append(result)
    
    return results


def _search_internal_index(
    query: str,
    submission_title: str,
    category: str,
    repo_root: str
) -> tuple:
    """
    Search the journal's own agent-index.json for related published articles.
    
    This is the most important search for SUPERSESSION DETECTION. If the new
    submission is on a very similar topic to an existing paper in our journal,
    we flag it as a potential supersession candidate. The Gemini reviewer
    (Stage 5) will then be asked to determine if this is:
      - A genuine update (new data, new findings)
      - A duplicate (same content, no new contribution)
      - A competing article (different perspective on same topic)
    
    Phase 1 uses simple keyword matching. Phase 2 will add cosine similarity
    on embeddings from _data/embeddings.json for better semantic matching.
    
    Returns:
        tuple of (results_list, potential_supersession_dict_or_none)
    """
    index_path = os.path.join(repo_root, "agent-index.json")
    
    try:
        with open(index_path, "r") as f:
            index_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return [], None
    
    papers = index_data.get("papers", [])
    if not papers:
        return [], None
    
    # Simple keyword matching: score each paper by word overlap with the query
    query_words = set(query.lower().split())
    # Remove very common words that don't help with matching
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "of", "in", 
                  "to", "for", "and", "or", "on", "with", "as", "by", "this",
                  "that", "it", "from", "at", "be", "has", "had", "have"}
    query_words -= stop_words
    
    scored_papers = []
    for paper in papers:
        paper_text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        paper_words = set(paper_text.split()) - stop_words
        
        if not query_words or not paper_words:
            continue
        
        # Jaccard-like similarity: intersection over union
        overlap = len(query_words & paper_words)
        union = len(query_words | paper_words)
        score = overlap / union if union > 0 else 0
        
        if overlap >= 3:  # Require at least 3 shared meaningful words
            scored_papers.append((score, paper))
    
    # Sort by score descending, take top 5
    scored_papers.sort(key=lambda x: x[0], reverse=True)
    top_papers = scored_papers[:5]
    
    results = []
    potential_supersession = None
    
    for score, paper in top_papers:
        result = {
            "source": "internal",
            "id": paper.get("id", ""),
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", "")[:500],
            "category": paper.get("category", ""),
            "score": paper.get("review_score"),
            "published_date": paper.get("published_date", ""),
            "similarity_score": round(score, 3),
            "status": paper.get("status", "current"),
        }
        results.append(result)
        
        # Check for potential supersession:
        # Same category + high keyword overlap + not already superseded
        if (score > 0.3 
            and paper.get("category") == category 
            and paper.get("status") != "superseded"
            and potential_supersession is None):
            potential_supersession = {
                "existing_paper_id": paper.get("id", ""),
                "existing_title": paper.get("title", ""),
                "similarity_score": round(score, 3),
                "message": (
                    f"This submission appears to be related to existing paper "
                    f"'{paper.get('title', '')}' (ID: {paper.get('id', '')}). "
                    f"The reviewer should determine if this is an update, "
                    f"duplicate, or independent contribution."
                ),
            }
    
    return results, potential_supersession
