"""Receives articles from Rankita (custom-site integration) into this blog.

Rankita POSTs each article signed as  Rankita-Signature: t=<unix>,v1=<hex HMAC-SHA256(secret, "<t>.<raw body>")>.
Events: test, article.published, article.updated. Test articles are saved as drafts;
the rest are published unless RANKITA_PUBLISH_MODE=draft.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

import db
from models import BlogPost
from routers.blog_render import CATEGORY_LABELS

SECRET = os.environ.get("RANKITA_WEBHOOK_SECRET", "")
PUBLISH = os.environ.get("RANKITA_PUBLISH_MODE", "publish") == "publish"
BASE_URL = os.environ.get("BASE_URL", "https://www.bsdcoaching.co.il")

router = APIRouter(prefix="/api", tags=["rankita"])


def _verify(raw: bytes, header: str | None) -> bool:
    if not SECRET or not header:
        return False
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    try:
        t = int(parts.get("t", ""))
    except ValueError:
        return False
    if abs(time.time() - t) > 300 or not parts.get("v1"):
        return False
    expected = hmac.new(SECRET.encode(), f"{t}.".encode() + raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(parts["v1"], expected)


@router.post("/rankita")
async def receive(request: Request):
    raw = await request.body()
    if not _verify(raw, request.headers.get("rankita-signature")):
        raise HTTPException(status_code=401, detail="invalid signature")

    payload = json.loads(raw)
    event, article = payload.get("event"), payload.get("article")
    if event == "test" and not article:
        return {"ok": True}
    if not article or not article.get("id") or not article.get("slug"):
        raise HTTPException(status_code=400, detail="missing article")

    slug = db.rankita_slug(article["id"])
    existing = db.get_post(slug) if slug else None
    if not existing:
        # Never overwrite an article this blog wrote itself that happens to share the slug
        slug = article["slug"]
        if db.get_post(slug):
            slug = f"{slug}-{str(article['id'])[:6]}"

    status = "published" if PUBLISH and event != "test" else "draft"
    content = article.get("content_markdown") or ""
    fields = {
        "title": article["title"],
        "content": content,
        "excerpt": article.get("meta_description") or content[:200],
        "category": article.get("category") if article.get("category") in CATEGORY_LABELS else "coaching",
        "keyword": article.get("keyword") or "",
        "meta_title": article.get("meta_title") or article["title"],
        "meta_description": article.get("meta_description"),
        "cover_image": article.get("cover_image_url"),
        "language": article.get("language") or "he",
        "status": status,
    }
    if existing:
        if existing.status == "published":  # an update never unpublishes or re-dates a live post
            fields["status"] = "published"
        elif status == "published":
            fields["published_at"] = article.get("published_at") or datetime.utcnow().isoformat()
        db.update_post(slug, fields)
    else:
        db.create_post(BlogPost(
            slug=slug,
            word_count=len(content.split()),
            published_at=(article.get("published_at") or datetime.utcnow().isoformat()) if status == "published" else None,
            **fields,
        ))
        db.link_rankita(article["id"], slug)

    published = fields["status"] == "published"
    return {"ok": True, "status": fields["status"], "url": f"{BASE_URL}/api/blog/{slug}" if published else None}
