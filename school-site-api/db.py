from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

from psycopg_pool import ConnectionPool

from models import BlogPost

DATABASE_URL = os.environ.get("DATABASE_URL", "")

_memory_store: dict[str, dict[str, Any]] = {}
_use_memory = not DATABASE_URL
_pool: ConnectionPool | None = None

# Simple TTL cache for published posts (60 seconds)
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 60


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and time.time() - entry[0] < CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any):
    _cache[key] = (time.time(), value)


def _cache_clear():
    _cache.clear()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS blog_posts (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    excerpt TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'coaching',
    keyword TEXT NOT NULL DEFAULT '',
    meta_title TEXT,
    meta_description TEXT,
    cover_image TEXT,
    video_url TEXT,
    author_name TEXT NOT NULL DEFAULT 'בית הספר לאימון יהודי BSD',
    author_role TEXT NOT NULL DEFAULT '',
    word_count INTEGER NOT NULL DEFAULT 0,
    language TEXT NOT NULL DEFAULT 'he',
    status TEXT NOT NULL DEFAULT 'draft',
    published_at TIMESTAMPTZ,
    scheduled_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_blog_status ON blog_posts(status);
CREATE INDEX IF NOT EXISTS idx_blog_language ON blog_posts(language);
CREATE INDEX IF NOT EXISTS idx_blog_published ON blog_posts(published_at DESC);
CREATE TABLE IF NOT EXISTS rankita_posts (
    external_id TEXT PRIMARY KEY,
    slug TEXT NOT NULL REFERENCES blog_posts(slug) ON DELETE CASCADE
);
"""


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(DATABASE_URL, min_size=2, max_size=5, open=True)
    return _pool


def init_db():
    if _use_memory:
        return
    pool = _get_pool()
    with pool.connection() as conn:
        conn.execute(SCHEMA_SQL)
        conn.commit()


def _row_to_post(row: dict) -> BlogPost:
    return BlogPost(
        slug=row["slug"],
        title=row["title"],
        content=row.get("content", ""),
        excerpt=row.get("excerpt", ""),
        category=row.get("category", "coaching"),
        keyword=row.get("keyword", ""),
        meta_title=row.get("meta_title"),
        meta_description=row.get("meta_description"),
        cover_image=row.get("cover_image"),
        video_url=row.get("video_url"),
        author_name=row.get("author_name", "בית הספר לאימון יהודי BSD"),
        author_role=row.get("author_role", ""),
        word_count=row.get("word_count", 0),
        language=row.get("language", "he"),
        status=row.get("status", "draft"),
        published_at=row["published_at"].isoformat() if row.get("published_at") else None,
        scheduled_date=str(row["scheduled_date"]) if row.get("scheduled_date") else None,
        created_at=row["created_at"].isoformat() if row.get("created_at") else "",
        updated_at=row["updated_at"].isoformat() if row.get("updated_at") else "",
    )


def list_posts(status: str | None = None, language: str = "he") -> list[BlogPost]:
    cache_key = f"list:{status}:{language}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    if _use_memory:
        posts = [BlogPost(**v) for v in _memory_store.values()]
        if status:
            posts = [p for p in posts if p.status == status]
        posts = [p for p in posts if p.language == language]
        posts.sort(key=lambda p: p.published_at or p.created_at, reverse=True)
        _cache_set(cache_key, posts)
        return posts

    with _get_pool().connection() as conn:
        if status:
            cur = conn.execute(
                "SELECT * FROM blog_posts WHERE status = %s AND language = %s ORDER BY published_at DESC NULLS LAST",
                (status, language),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM blog_posts WHERE language = %s ORDER BY published_at DESC NULLS LAST",
                (language,),
            )
        rows = [dict(zip([d.name for d in cur.description], r)) for r in cur.fetchall()]
        posts = [_row_to_post(r) for r in rows]
        _cache_set(cache_key, posts)
        return posts


def get_post(slug: str) -> BlogPost | None:
    cache_key = f"post:{slug}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    if _use_memory:
        data = _memory_store.get(slug)
        post = BlogPost(**data) if data else None
        if post:
            _cache_set(cache_key, post)
        return post

    with _get_pool().connection() as conn:
        cur = conn.execute("SELECT * FROM blog_posts WHERE slug = %s", (slug,))
        row = cur.fetchone()
        if not row:
            return None
        post = _row_to_post(dict(zip([d.name for d in cur.description], row)))
        _cache_set(cache_key, post)
        return post


def create_post(post: BlogPost) -> BlogPost:
    _cache_clear()
    if _use_memory:
        _memory_store[post.slug] = post.model_dump()
        return post

    with _get_pool().connection() as conn:
        conn.execute(
            """INSERT INTO blog_posts (slug, title, content, excerpt, category, keyword,
               meta_title, meta_description, cover_image, video_url, author_name, author_role,
               word_count, language, status, published_at, scheduled_date)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (post.slug, post.title, post.content, post.excerpt, post.category, post.keyword,
             post.meta_title, post.meta_description, post.cover_image, post.video_url,
             post.author_name, post.author_role, post.word_count, post.language, post.status,
             post.published_at, post.scheduled_date),
        )
        conn.commit()
    return post


def update_post(slug: str, updates: dict[str, Any]) -> BlogPost | None:
    _cache_clear()
    existing = get_post(slug)
    if not existing:
        return None

    for key, value in updates.items():
        if value is not None:
            setattr(existing, key, value)
    existing.updated_at = datetime.utcnow().isoformat()
    existing.word_count = len(existing.content.split())

    if _use_memory:
        _memory_store[slug] = existing.model_dump()
        return existing

    with _get_pool().connection() as conn:
        conn.execute(
            """UPDATE blog_posts SET title=%s, content=%s, excerpt=%s, category=%s, keyword=%s,
               meta_title=%s, meta_description=%s, cover_image=%s, video_url=%s, author_name=%s,
               word_count=%s, language=%s, status=%s, published_at=%s, scheduled_date=%s,
               updated_at=NOW()
               WHERE slug=%s""",
            (existing.title, existing.content, existing.excerpt, existing.category, existing.keyword,
             existing.meta_title, existing.meta_description, existing.cover_image, existing.video_url,
             existing.author_name, existing.word_count, existing.language, existing.status,
             existing.published_at, existing.scheduled_date, slug),
        )
        conn.commit()
    return existing


def delete_post(slug: str) -> bool:
    _cache_clear()
    if _use_memory:
        return _memory_store.pop(slug, None) is not None

    with _get_pool().connection() as conn:
        cur = conn.execute("DELETE FROM blog_posts WHERE slug = %s", (slug,))
        conn.commit()
        return cur.rowcount > 0


def publish_post(slug: str) -> BlogPost | None:
    return update_post(slug, {
        "status": "published",
        "published_at": datetime.utcnow().isoformat(),
    })


def rankita_slug(external_id: str) -> str | None:
    """Slug of the blog post a Rankita article was saved as, if any."""
    if _use_memory:
        return _rankita_memory.get(external_id)
    with _get_pool().connection() as conn:
        row = conn.execute("SELECT slug FROM rankita_posts WHERE external_id = %s", (external_id,)).fetchone()
        return row[0] if row else None


def link_rankita(external_id: str, slug: str):
    if _use_memory:
        _rankita_memory[external_id] = slug
        return
    with _get_pool().connection() as conn:
        conn.execute(
            "INSERT INTO rankita_posts (external_id, slug) VALUES (%s, %s) ON CONFLICT (external_id) DO UPDATE SET slug = EXCLUDED.slug",
            (external_id, slug),
        )
        conn.commit()


_rankita_memory: dict[str, str] = {}
