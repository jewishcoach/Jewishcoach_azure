"""AI Article Generation — Azure OpenAI GPT for BSD coaching content."""

from __future__ import annotations

import hmac
import os
import re
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from auth import require_admin
from models import BlogPost
import db

router = APIRouter(prefix="/api/admin/content", tags=["generation"])

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

BASE_URL = os.environ.get("BASE_URL", "https://www.bsdcoaching.co.il")


BSD_BRAND_VOICE = """אתה כותב תוכן עבור בית הספר לאימון יהודי בשיטת BSD, שהקים בני גל ז"ל.
השנה הנוכחית היא 2026.

על השיטה:
שיטת BSD היא שיטת אימון יהודי ייחודית שפותחה לאורך 25 שנה. ששת היסודות:
1. אדם הוא עולם ומקדש — כל אדם הוא שלם ומלא פוטנציאל
2. חזון וסולם החזון — בניית תמונת עתיד ברורה ודרך מעשית להגיע אליה
3. מדדים (שעונים) — כלים למדידת התקדמות אמיתית
4. העסק הוא לא אתה — הפרדה בריאה בין זהות לעשייה
5. ערכים ומשמעות — פעולה מתוך ערכי ליבה
6. פריצת דרך — זיהוי רגעי שינוי ומינופם

במרכז השיטה: "תהליך השיבה" — מודל ייחודי המאפשר גילוי שליחות, התמרת חסמים לכוחות, וקבלת כלים מעשיים.

קהל יעד: מנהלים, יזמים, מאמנים, אנשי עסקים ישראלים המחפשים כלים מבוססי מורשת יהודית.

סגנון כתיבה:
- עברית מדוברת, חמה, אישית — כמו שיחה עם מאמן
- שילוב טבעי של מושגים מהמסורת היהודית עם עולם הניהול המודרני
- משפטים קצרים. דוגמאות מעשיות. משלים.
- בלי ביטויים אקדמיים מנופחים
- מותר לצטט חז"ל, מדרשים, פסוקים — תמיד בהקשר מעשי
- כל מאמר צריך לתת ערך מיידי — כלי, תרגיל, או נקודת מבט שאפשר ליישם היום
- אורך: 1200-1800 מילים
- שלב לפחות כותרת H2 אחת שמסתיימת בסימן שאלה (לצורך FAQ schema)

מבנה תגובה:
TITLE: כותרת מושכת בעברית (עד 60 תווים)
META_DESCRIPTION: תיאור SEO בעברית (עד 155 תווים, ללא markdown)
CATEGORY: אחת מ: coaching, leadership, methodology, parasha, business
---
[תוכן המאמר ב-markdown]
"""


KEYWORD_SCHEDULE_HE: dict[str, str] = {
    # Week 1-2: Quick wins (low competition, high relevance)
    "2026-09-02": "אימון אישי לחיים",
    "2026-09-04": "משבר גיל 40",
    "2026-09-06": "לוח חזון אישי",
    "2026-09-08": "ייעוץ זוגי דתי",
    "2026-09-10": "משבר גיל 40 ביהדות",
    # Week 3-4: Core topics
    "2026-09-12": "קואצ'ינג מה זה",
    "2026-09-14": "כמה עולה אימון אישי",
    "2026-09-16": "שינוי קריירה בגיל 40",
    "2026-09-18": "אימון עסקי למנהלים",
    "2026-09-20": "ספרי התפתחות אישית",
    # Week 5-6: Authority building
    "2026-09-23": "אימון אישי",
    "2026-09-26": "איפה מומלץ ללמוד אימון אישי",
    "2026-09-29": "פיתוח מנהלים",
    "2026-10-02": "אימון זוגי",
    "2026-10-05": "הכשרת מאמנים",
    # Week 7-8: Funnel / conversion
    "2026-10-08": "קורס אימון אישי",
    "2026-10-11": "לימודי קואצ'ינג",
    "2026-10-14": "קואצ'ר מומלץ",
    "2026-10-17": "ייעוץ עסקי לעסקים קטנים",
    "2026-10-20": "סדנת מנהיגות",
    # Week 9-12: Depth & authority
    "2026-10-23": "משבר אמצע החיים",
    "2026-10-26": "שינוי קריירה בגיל 50",
    "2026-10-29": "קואצ'ינג אישי",
    "2026-11-01": "ייעוץ זוגי לדתיים",
    "2026-11-04": "אימון אישי לבני נוער",
    "2026-11-07": "בני גל ושיטת BSD",
    "2026-11-10": "התפתחות אישית",
    "2026-11-13": "קורס אימון אישי חינם",
    "2026-11-16": "פיתוח מנהלים מחיר",
    "2026-11-19": "ייעוץ זוגי חינם",
}

BLOG_CRON_SECRET = os.environ.get("BLOG_CRON_SECRET", "").strip()


async def _require_cron_secret(x_blog_cron_secret: str = Header("")):
    if not BLOG_CRON_SECRET:
        raise HTTPException(503, "BLOG_CRON_SECRET not configured on server")
    if not x_blog_cron_secret or not hmac.compare_digest(x_blog_cron_secret, BLOG_CRON_SECRET):
        raise HTTPException(403, "Invalid cron secret")


class GenerateRequest(BaseModel):
    keyword: str
    scheduled_date: str | None = None


class CronResponse(BaseModel):
    status: str
    post_slug: str | None = None
    title: str | None = None
    message: str = ""


async def _call_azure_openai(system_prompt: str, user_prompt: str) -> str:
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_KEY:
        raise HTTPException(503, "Azure OpenAI not configured")

    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            url,
            headers={"api-key": AZURE_OPENAI_KEY, "Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_completion_tokens": 4000,
            },
        )
        if resp.status_code != 200:
            raise HTTPException(502, f"Azure OpenAI error: {resp.status_code} {resp.text[:200]}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def _parse_generated(text: str) -> dict:
    title = ""
    meta = ""
    category = "coaching"
    content = ""

    title_m = re.search(r"TITLE:\s*(.+)", text)
    meta_m = re.search(r"META_DESCRIPTION:\s*(.+)", text)
    cat_m = re.search(r"CATEGORY:\s*(.+)", text)

    if title_m:
        title = title_m.group(1).strip()
    if meta_m:
        meta = meta_m.group(1).strip()
    if cat_m:
        category = cat_m.group(1).strip().lower()

    parts = text.split("---", 1)
    if len(parts) == 2:
        content = parts[1].strip()
    elif not title_m:
        content = text.strip()

    return {"title": title, "meta_description": meta, "category": category, "content": content}


def _build_internal_links_context() -> str:
    published = db.list_posts(status="published")
    if not published:
        return ""
    links = []
    for p in published[:15]:
        links.append(f"- [{p.title}]({BASE_URL}/blog/{p.slug})")
    return "\n\nלינקים פנימיים שאפשר לשלב בתוכן (שלב 2-3 בצורה טבעית):\n" + "\n".join(links)


def _slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^\w\s֐-׿-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-") or "post"


@router.post("/generate")
async def generate_article(body: GenerateRequest, _=Depends(require_admin)):
    links_ctx = _build_internal_links_context()
    user_prompt = f"כתוב מאמר SEO מקיף על הנושא: {body.keyword}{links_ctx}"

    raw = await _call_azure_openai(BSD_BRAND_VOICE, user_prompt)
    parsed = _parse_generated(raw)

    if not parsed["title"]:
        parsed["title"] = body.keyword

    slug = _slugify(parsed["title"])
    if db.get_post(slug):
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

    post = BlogPost(
        slug=slug,
        title=parsed["title"],
        content=parsed["content"],
        excerpt=parsed["content"][:200].replace("#", "").replace("*", "").strip(),
        category=parsed["category"],
        keyword=body.keyword,
        meta_title=parsed["title"],
        meta_description=parsed["meta_description"],
        cover_image=f"{BASE_URL}/api/public/blog-cover/{slug}",
        word_count=len(parsed["content"].split()),
        status="draft",
        scheduled_date=body.scheduled_date,
    )

    db.create_post(post)
    return {"slug": post.slug, "title": post.title, "word_count": post.word_count, "status": "draft"}


@router.post("/cron/daily")
async def daily_cron(_=Depends(_require_cron_secret)) -> CronResponse:
    today = datetime.utcnow().strftime("%Y-%m-%d")

    keyword = KEYWORD_SCHEDULE_HE.get(today)
    if not keyword:
        return CronResponse(status="skipped", message=f"No keyword scheduled for {today}")

    existing = db.list_posts(status="published")
    if any(p.keyword == keyword for p in existing):
        return CronResponse(status="skipped", message=f"Article for '{keyword}' already exists")

    links_ctx = _build_internal_links_context()
    user_prompt = f"כתוב מאמר SEO מקיף על הנושא: {keyword}{links_ctx}"

    raw = await _call_azure_openai(BSD_BRAND_VOICE, user_prompt)
    parsed = _parse_generated(raw)

    if not parsed["title"]:
        parsed["title"] = keyword

    slug = _slugify(parsed["title"])
    if db.get_post(slug):
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

    post = BlogPost(
        slug=slug,
        title=parsed["title"],
        content=parsed["content"],
        excerpt=parsed["content"][:200].replace("#", "").replace("*", "").strip(),
        category=parsed["category"],
        keyword=keyword,
        meta_title=parsed["title"],
        meta_description=parsed["meta_description"],
        cover_image=f"{BASE_URL}/api/public/blog-cover/{slug}",
        word_count=len(parsed["content"].split()),
        status="published",
        published_at=datetime.utcnow().isoformat(),
    )

    db.create_post(post)

    # TODO: trigger video job
    # TODO: post to Facebook

    return CronResponse(status="published", post_slug=post.slug, title=post.title)
