#!/usr/bin/env python3
"""
One-time migration: papers/{paper_id}/article.md  →  papers/{journal}/{topic}/{slug}/index.md

Run from repo root:
  python3 scripts/migrate_papers_to_journal_topic_layout.py

Preserves legacy URLs via Hugo `aliases` in frontmatter. Updates agent-index.json
article_path and reader_url for each moved paper.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "_review_agent"))

from pubroot_site_paths import (  # noqa: E402
    legacy_hugo_aliases,
    parse_journal_topic,
    reader_url,
    slugify_title,
    normalize_title_for_slug,
)

PUBROOT_SITE_BASE = os.environ.get("PUBROOT_SITE_BASE", "https://pubroot.com")
_PAPER_DIR_RE = re.compile(r"^2026-\d{3}$")


def _inject_aliases_into_frontmatter(text: str, paper_id: str) -> str:
    """Append Hugo aliases for old /{paper_id}/article/ URLs before the closing ---."""
    if not text.lstrip().startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    middle = parts[1]
    if "aliases:" in middle:
        return text
    aliases = legacy_hugo_aliases(paper_id)
    block = "\naliases:\n" + "\n".join(f"  - {json.dumps(a)}" for a in aliases) + "\n"
    new_middle = middle.rstrip() + block
    return f"---{new_middle}---{parts[2]}"


def _parse_title_and_category(middle: str) -> tuple[str, str]:
    """Extract title and category from frontmatter text for slug and path."""
    title = "untitled"
    category = ""
    for line in middle.split("\n"):
        ls = line.strip()
        if ls.lower().startswith("title:"):
            raw = ls.split(":", 1)[1].strip()
            try:
                title = json.loads(raw)
            except json.JSONDecodeError:
                title = raw.strip('"').strip("'")
        if ls.lower().startswith("category:"):
            raw = ls.split(":", 1)[1].strip()
            try:
                category = json.loads(raw)
            except json.JSONDecodeError:
                category = raw.strip('"').strip("'")
    return title, category


def main() -> int:
    papers_root = _REPO_ROOT / "papers"
    index_path = _REPO_ROOT / "agent-index.json"
    mappings: dict[str, dict] = {}

    for child in sorted(papers_root.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if not _PAPER_DIR_RE.match(name):
            continue
        old_article = child / "article.md"
        old_manifest = child / "manifest.json"
        if not old_article.is_file():
            continue

        raw = old_article.read_text(encoding="utf-8")
        if not raw.lstrip().startswith("---"):
            print(f"SKIP (no FM): {old_article}")
            continue
        parts = raw.split("---", 2)
        if len(parts) < 3:
            continue
        middle = parts[1]
        title, category = _parse_title_and_category(middle)
        title = normalize_title_for_slug(title)
        journal, topic = parse_journal_topic(category)
        slug = slugify_title(title, name)

        dest_dir = papers_root / journal / topic / slug
        dest_index = dest_dir / "index.md"
        if dest_index.exists():
            print(f"SKIP exists: {dest_index}")
            continue

        dest_dir.mkdir(parents=True, exist_ok=True)
        new_text = _inject_aliases_into_frontmatter(raw, name)
        dest_index.write_text(new_text, encoding="utf-8")

        if old_manifest.is_file():
            shutil.copy2(old_manifest, dest_dir / "manifest.json")

        new_article_path = f"papers/{journal}/{topic}/{slug}/index.md"
        mappings[name] = {
            "article_path": new_article_path,
            "reader_url": reader_url(PUBROOT_SITE_BASE, journal, topic, slug),
        }

        shutil.rmtree(child)
        print(f"OK {name} -> {new_article_path}")

    if mappings and index_path.is_file():
        data = json.loads(index_path.read_text(encoding="utf-8"))
        for entry in data.get("papers", []):
            pid = entry.get("id")
            if pid in mappings:
                entry["article_path"] = mappings[pid]["article_path"]
                entry["reader_url"] = mappings[pid]["reader_url"]
        index_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Updated agent-index.json ({len(mappings)} papers)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
