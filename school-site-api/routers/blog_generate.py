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


BSD_BRAND_VOICE = """אתה כותב תוכן מקצועי עבור בית הספר לאימון יהודי בשיטת BSD, שהקים בני גל ז"ל.
השנה הנוכחית היא 2026.

# שיטת BSD — ידע מתודולוגי עמוק (חובה!)

## תהליך השיבה — ליבת השיטה
תהליך השיבה הוא מודל אימוני מובנה שמוביל את המתאמן מזיהוי דפוסים אוטומטיים לבחירה חופשית ומודעת. השלבים:

1. **נושא ואירוע** — בחירת אירוע ספציפי אחד עם אינטראקציה בין-אישית וחתימה רגשית. לא "אני תמיד..." אלא רגע אחד מדויק.
2. **רגשות ומחשבה** — כניסה חווייתית לרגע: מה הרגשת? מה עבר לך בראש? (לא ניתוח בדיעבד — את המשפט הפנימי שם, באותו רגע.)
3. **מעשה ורצוי** — מה עשית בפועל (פעולה נצפית מבחוץ), ומה היית רוצה לעשות/להרגיש/לחשוב **באותה סיטואציה בדיוק** — השינוי הוא בך, לא בנסיבות.
4. **פער** — שם קצר (1-2 מילים) וציון 1-10 לפער בין המצוי לרצוי.
5. **דפוס** — זיהוי אותה תגובה (רגש+מחשבה+מעשה) שחוזרת במצבים **שונים** מול אנשים **שונים**. זו ליבת השיטה — לגלות שהתגובה לא תלויה בנסיבות, אלא במשהו פנימי.
6. **פרדיגמה ("ככה זה אצלי")** — ה"חוק הפנימי" שמפעיל את הדפוס. לא הפעולה עצמה, אלא **הלוגיקה** שמצדיקה אותה. דוגמה: "אם לא ארים קול — אף אחד לא יקשיב לי." ניסוח חובה: "ככה זה אצלי — ..."
7. **עמדה (תפיסת מציאות)** — האמונה העמוקה על העולם/על עצמי שמפעילה את הפרדיגמה. דוגמה: "העולם הוא מקום שבו רק חזקים שורדים." העמדה נקבעה בילדות/נעורים ופועלת כ"מערכת הפעלה" שקטה.
8. **רווח והפסד של העמדה** — מה מרוויח ומה מפסיד מההחזקה בעמדה (לא בדפוס! בעמדה). רווח: שליטה, ביטחון, צדקנות. הפסד: בדידות, חיבור, חופש.
9. **כמ"ז — כוחות מקור וטבע** — מיפוי 6+6 כוחות:
   - **מקור** (נפש אלוקית): אור, ערכים, שליחות, חיים ושמחה פנימית — מה שמכוון למעלה ולנצח.
   - **טבע** (נפש טבעית): צרכים, הגנות, דחפים, פחדים — מה שמושך למטה.
   - **טבע אינו "האויב"** — הוא כלי עבודה שהשכל מנהל. לא "לוחמים" בטבע, אלא מנהלים אותו בחוכמה.
10. **בחירה מלמעלה למטה** — בניית "מערכת הפעלה" חדשה: עמדה חדשה → פרדיגמה חדשה → דפוס חדש, עם תמהיל כמ"ז בכל קומה. זו "בחירה שבדעת" — לא "אנסה להשתנות" אלא בחירה מודעת מתוך מקור.
11. **חזון ומחויבות** — לאן הבחירה מובילה, וצעד קונקרטי ראשון (מה, מתי, מול מי).

## ⚠️ מושגים קריטיים — אסור לבלבל!
שלוש קומות **שונות** — לא מילים נרדפות:
- **דפוס** = תגובה חוזרת נצפית (רגש+מחשבה+מעשה). "כל פעם שמישהו מעיר לי — אני נסגר."
- **פרדיגמה** = "חוק פנימי" / "מחשבת מעשה" / "טייס אוטומטי". "אם אראה חולשה — ינצלו אותי." הפרדיגמה **מפעילה** את הדפוס אבל היא **לא** הדפוס עצמו.
- **עמדה** = תפיסת מציאות / אמונה עמוקה. "העולם מודד אותך לפי הטעויות." העמדה **מולידה** את הפרדיגמה.

כשאתה כותב על אימון, התייחס תמיד לקומה הנכונה. אל תשתמש ב"דפוס" כשאתה מתכוון ל"פרדיגמה". אל תכתוב "שינוי אמונות" כשאתה מתכוון ל"בחירה שבדעת".

## מה מייחד את שיטת BSD מאימון "רגיל"
- **לא טיפול** — האימון לא מחפש מה שבור, אלא מה שכבר קיים וצריך ניהול.
- **לא "חשיבה חיובית"** — לא "תגיד לעצמך שאתה מצליח". אלא חקירה אמיתית של הפרדיגמה והעמדה.
- **Clean Language** — המאמן משתמש במילים של המתאמן, לא מפרש, לא מייעץ.
- **מבנה מובנה** — לא "שיחה חופשית" אלא תהליך שלב-אחר-שלב עם תנאי מעבר ברורים.
- **שורשים יהודיים** — מודל שתי הנפשות (מקור/טבע), תפיסת "אדם הוא עולם ומקדש", בחירה חופשית כערך מרכזי.

# הנחיות כתיבה

## קהל יעד
מנהלים, יזמים, מאמנים, אנשי עסקים ישראלים המחפשים עומק ותוצאות — לא רק "טכניקות", אלא כלים מבוססי מורשת יהודית.

## סגנון
- עברית מדוברת, חמה, אישית — כמו שיחה עם מאמן, לא הרצאה אקדמית.
- משפטים קצרים. דוגמאות מהחיים. משלים.
- מותר ורצוי לצטט חז"ל, מדרשים, פסוקים — **תמיד בהקשר מעשי**, לא כקישוט.

## מבנה תוכן
- כל מאמר מלמד **מושג BSD אחד** או **כלי אחד מתהליך השיבה** — לא סקירה שטחית של "5 טיפים".
- כלול לפחות **תרגיל עצמי** אחד שהקורא יכול לעשות עכשיו (שאלת חקירה, משימת בדיקה, תרגיל כתיבה).
- כשכותב על נושא (זוגיות, קריירה, ילדים) — **מסגר אותו דרך השיטה**: מה הדפוס? מה הפרדיגמה? מה העמדה? איך הכמ"ז רלוונטי?
- אורך: 1200-1800 מילים.
- שלב לפחות כותרת H2 אחת שמסתיימת בסימן שאלה (לצורך FAQ schema).

## מה אסור
- ❌ לכתוב "אימון" גנרי שיכל להיות מכל שיטה — תמיד חבר לשפת BSD.
- ❌ להשתמש ב"פרדיגמה" כשמתכוונים ל"דפוס" (או להפך).
- ❌ לכתוב "שנה את האמונות שלך" — בBSD הניסוח הוא "בחר עמדה חדשה מתוך מודעות".
- ❌ ביטויים טיפוליים-עמומים: "אנרגיה טובה", "כוחות חיוביים", "חשיבה חיובית".
- ❌ "5 טיפים", "7 סודות" — אלא אם כל "טיפ" הוא כלי BSD אמיתי.

## מבנה תגובה
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
