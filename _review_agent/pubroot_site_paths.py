"""
Pubroot site path helpers — journal/topic/slug layout for SEO-friendly URLs.

WHY THIS MODULE EXISTS (Apr 2026):
    Published articles previously lived at papers/{paper_id}/article.md, which
    Hugo rendered as /{paper_id}/article/ — weak for topical SEO. The new layout
    mirrors the submission category (journal/topic) plus a title-derived slug:

        papers/{journal}/{topic}/{slug}/index.md
        → https://pubroot.com/{journal}/{topic}/{slug}/

    Reviews stay at reviews/{paper_id}/review.json so existing client-side fetch
    paths and tooling keyed by paper_id remain stable.

    Legacy URLs are preserved via Hugo frontmatter `aliases` so inbound links and
    search indexes do not break during migration.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


def normalize_title_for_slug(raw_title: str) -> str:
    """
    Strip JSON-style escaping and outer quotes that the pipeline sometimes embeds
    in published titles (e.g. '\\\"A Field Taxonomy...\\\"' or plain quotes).
    """
    t = raw_title.strip()
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1]
    t = t.replace('\\"', '"').replace("\\'", "'")
    return t.strip()


def slugify_title(title: str, paper_id: str, max_len: int = 140) -> str:
    """
    Build a URL path segment from the article title.

    Falls back to paper_id if the slug would be empty. Keeps length bounded for
    filesystem and URL hygiene. Uses ASCII letters, digits, and hyphens only.
    """
    t = normalize_title_for_slug(title)
    s = t.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s:
        s = paper_id
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s


def parse_journal_topic(category: str) -> Tuple[str, str]:
    """
    Split category 'journal/topic' into path segments. Unknown or legacy flat
    categories map to 'general/general' only for the path — frontmatter category
    string stays unchanged for display and metadata.
    """
    cat = (category or "").strip()
    if "/" in cat:
        j, _, rest = cat.partition("/")
        j = j.strip() or "general"
        t = rest.strip() or "general"
        return _sanitize_segment(j), _sanitize_segment(t)
    if cat:
        return _sanitize_segment(cat), "general"
    return "general", "general"


def _sanitize_segment(seg: str) -> str:
    """Allow only safe path characters (match journal slugs in journals.json)."""
    s = seg.lower().strip()
    s = re.sub(r"[^a-z0-9_-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "general"


def publication_dir_rel(journal: str, topic: str, slug: str) -> str:
    """Relative directory under repo root: papers/{journal}/{topic}/{slug}/"""
    return f"papers/{journal}/{topic}/{slug}"


def article_index_rel(journal: str, topic: str, slug: str) -> str:
    """Hugo leaf page path (index bundle)."""
    return f"{publication_dir_rel(journal, topic, slug)}/index.md"


def manifest_rel(journal: str, topic: str, slug: str) -> str:
    """Manifest co-located with the article bundle."""
    return f"{publication_dir_rel(journal, topic, slug)}/manifest.json"


def legacy_hugo_aliases(paper_id: str) -> list:
    """
    Old permalink patterns to register as Hugo aliases after migration.

    Historical builds emitted /{paper_id}/article/ and /{paper_id}/ for the same
    paper (see sitemap). Both are listed so either old link keeps working.
    """
    return [
        f"/{paper_id}/article/",
        f"/{paper_id}/",
    ]


def unique_slug(
    base_slug: str,
    paper_id: str,
    reserved: Optional[set] = None,
) -> str:
    """
    Ensure uniqueness within a (journal, topic) namespace. If base_slug is
    taken, append -{paper_id} so concurrent publishes never collide.
    """
    reserved = reserved or set()
    if base_slug not in reserved:
        return base_slug
    suffixed = f"{base_slug}-{paper_id}"
    if suffixed not in reserved:
        return suffixed
    return f"{base_slug}-{paper_id}-x"


def reader_url(base_url: str, journal: str, topic: str, slug: str) -> str:
    """Canonical https URL for humans and agent-index (trailing slash)."""
    base = base_url.rstrip("/") + "/"
    return f"{base}{journal}/{topic}/{slug}/"
