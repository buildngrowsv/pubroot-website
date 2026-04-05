"""Tests for pubroot_site_paths SEO path helpers."""

from pubroot_site_paths import (
    legacy_hugo_aliases,
    parse_journal_topic,
    reader_url,
    slugify_title,
    normalize_title_for_slug,
)


def test_slugify_basic():
    s = slugify_title("A Field Taxonomy of Revenue Blockers", "2026-038")
    assert s == "a-field-taxonomy-of-revenue-blockers"
    # Default max_len=140 avoids chopping long technical titles mid-word.
    assert len(slugify_title("x" * 200, "2026-001")) <= 140


def test_parse_journal_topic():
    assert parse_journal_topic("ai/agent-architecture") == ("ai", "agent-architecture")
    assert parse_journal_topic("") == ("general", "general")


def test_reader_url():
    assert (
        reader_url("https://pubroot.com", "ai", "agent-architecture", "my-slug")
        == "https://pubroot.com/ai/agent-architecture/my-slug/"
    )


def test_legacy_aliases():
    assert f"/2026-038/article/" in legacy_hugo_aliases("2026-038")


def test_normalize_escaped_title():
    t = normalize_title_for_slug('"Hello World"')
    assert "Hello World" in t or t == "Hello World"
