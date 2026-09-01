from __future__ import annotations

import os
import re
from datetime import datetime

import markdown
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import db

router = APIRouter(prefix="/api", tags=["blog-render"])

BASE_URL = os.environ.get("BASE_URL", "https://www.bsdcoaching.co.il")

templates = Jinja2Templates(directory="templates")


def _extract_faq(html: str) -> list[dict[str, str]]:
    """Extract FAQ items from H2 headings that end with ?"""
    faq = []
    pattern = re.compile(r"<h2[^>]*>(.*?\?)</h2>(.*?)(?=<h2|$)", re.DOTALL)
    for match in pattern.finditer(html):
        question = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        answer_html = match.group(2).strip()
        answer = re.sub(r"<[^>]+>", "", answer_html).strip()
        answer = " ".join(answer.split()[:100])
        if question and answer:
            faq.append({"question": question, "answer": answer})
    return faq


def _md_to_html(content: str) -> str:
    return markdown.markdown(
        content,
        extensions=["tables", "fenced_code", "nl2br"],
    )


def _split_for_cta(html: str) -> tuple[str, str]:
    """Split HTML after the 3rd H2 heading for inline CTA injection."""
    import re
    h2_pattern = re.compile(r"<h2[^>]*>")
    matches = list(h2_pattern.finditer(html))
    if len(matches) >= 3:
        split_pos = matches[2].start()
        return html[:split_pos], html[split_pos:]
    elif len(matches) >= 2:
        split_pos = matches[1].start()
        return html[:split_pos], html[split_pos:]
    mid = len(html) // 2
    p_tag = html.find("</p>", mid)
    if p_tag > 0:
        split_pos = p_tag + 4
        return html[:split_pos], html[split_pos:]
    return html, ""


CATEGORY_LABELS = {
    "coaching": "אימון",
    "leadership": "מנהיגות",
    "methodology": "מתודולוגיה",
    "parasha": "פרשת שבוע",
    "business": "עסקים",
}


@router.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request, q: str = "", category: str = ""):
    posts = db.list_posts(status="published", language="he")

    all_categories = sorted(set(p.category for p in posts))

    if category:
        posts = [p for p in posts if p.category == category]
    if q:
        q_lower = q.strip()
        posts = [p for p in posts if q_lower in p.title or q_lower in p.content or q_lower in p.excerpt]

    return templates.TemplateResponse("blog_index.html", {
        "request": request,
        "posts": posts,
        "all_categories": all_categories,
        "category_labels": CATEGORY_LABELS,
        "active_category": category,
        "search_query": q,
        "title": "בלוג · בית הספר לאימון יהודי BSD",
        "description": "מאמרים, תובנות וכלים מעולם האימון היהודי בשיטת BSD",
        "canonical_url": f"{BASE_URL}/blog",
        "og_image": None,
        "year": datetime.utcnow().year,
    })


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str):
    post = db.get_post(slug)
    if not post or post.status != "published":
        return HTMLResponse("<h1>404 — הדף לא נמצא</h1>", status_code=404)

    content_html = _md_to_html(post.content)
    faq_items = _extract_faq(content_html)
    content_before_cta, content_after_cta = _split_for_cta(content_html)
    cover = post.cover_image or f"{BASE_URL}/api/public/blog-cover/{slug}"

    all_posts = db.list_posts(status="published", language="he")
    related = [p for p in all_posts if p.category == post.category and p.slug != slug][:3]

    return templates.TemplateResponse("blog_post.html", {
        "request": request,
        "post": post,
        "content_before_cta": content_before_cta,
        "content_after_cta": content_after_cta,
        "faq_items": faq_items,
        "related_posts": related,
        "title": post.meta_title or post.title,
        "description": post.meta_description or post.excerpt or post.content[:160],
        "canonical_url": f"{BASE_URL}/blog/{slug}",
        "base_url": BASE_URL,
        "og_type": "article",
        "og_image": cover,
        "year": datetime.utcnow().year,
    })
