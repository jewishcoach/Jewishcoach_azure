from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from auth import require_admin
from models import BlogPost, BlogPostCreate, BlogPostUpdate
import db

router = APIRouter(prefix="/api/admin/content", tags=["blog"])
public_router = APIRouter(prefix="/api/blog", tags=["blog-public"])


def _strip_md(text: str) -> str:
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"\n+", " ", text)
    return text.strip()[:160]


def _slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^\w\s֐-׿-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text.strip("-")
    return text or "post"


# ── Public endpoints ──

@public_router.get("/posts")
async def list_published(language: str = "he") -> list[BlogPost]:
    return db.list_posts(status="published", language=language)


@public_router.get("/posts/{slug}")
async def get_published(slug: str) -> BlogPost:
    post = db.get_post(slug)
    if not post or post.status != "published":
        raise HTTPException(status_code=404, detail="Post not found")
    return post


# ── Admin endpoints ──

@router.get("/stats")
async def content_stats(_=Depends(require_admin)):
    published = db.list_posts(status="published")
    drafts = db.list_posts(status="draft")
    scheduled = db.list_posts(status="scheduled")
    total_words = sum(p.word_count for p in published)
    return {
        "published": len(published),
        "drafts": len(drafts),
        "scheduled": len(scheduled),
        "total_words": total_words,
    }


@router.get("/posts")
async def admin_list_posts(status: str | None = None, _=Depends(require_admin)) -> list[BlogPost]:
    return db.list_posts(status=status)


@router.get("/posts/{slug}")
async def admin_get_post(slug: str, _=Depends(require_admin)) -> BlogPost:
    post = db.get_post(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts")
async def create_post(body: BlogPostCreate, _=Depends(require_admin)) -> BlogPost:
    slug = _slugify(body.title)
    if db.get_post(slug):
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

    post = BlogPost(
        slug=slug,
        title=body.title,
        content=body.content,
        excerpt=body.excerpt or body.content[:200],
        category=body.category,
        keyword=body.keyword,
        meta_title=body.meta_title or body.title,
        meta_description=body.meta_description or _strip_md(body.excerpt or body.content[:200]),
        cover_image=body.cover_image,
        video_url=body.video_url,
        author_name=body.author_name,
        language=body.language,
        status=body.status,
        scheduled_date=body.scheduled_date,
        word_count=len(body.content.split()),
        published_at=datetime.utcnow().isoformat() if body.status == "published" else None,
    )
    return db.create_post(post)


@router.patch("/posts/{slug}")
async def update_post(slug: str, body: BlogPostUpdate, _=Depends(require_admin)) -> BlogPost:
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = db.update_post(slug, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Post not found")
    return result


@router.post("/posts/{slug}/publish")
async def publish_post(slug: str, _=Depends(require_admin)) -> BlogPost:
    result = db.publish_post(slug)
    if not result:
        raise HTTPException(status_code=404, detail="Post not found")
    return result


@router.delete("/posts/{slug}")
async def delete_post(slug: str, _=Depends(require_admin)):
    if not db.delete_post(slug):
        raise HTTPException(status_code=404, detail="Post not found")
    return {"deleted": slug}
