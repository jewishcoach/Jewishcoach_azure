"""Migrate articles.json → blog API (PostgreSQL)."""

import json
import re
import sys
import httpx

API_URL = sys.argv[1] if len(sys.argv) > 1 else "https://bsd-blog-api.politesmoke-e98aa123.eastus.azurecontainerapps.io"
API_KEY = sys.argv[2] if len(sys.argv) > 2 else "dev-key-change-me"
ARTICLES_PATH = "/home/ishai/code/Jewishcoach_azure/school-site/src/data/articles.json"
BASE_URL = "https://www.bsdcoaching.co.il"

CATEGORY_KEYWORDS = {
    "coaching": ["אימון", "מאמן", "תהליך", "שיבה"],
    "leadership": ["ניהול", "מנהיג", "עובד", "צוות", "עסק"],
    "methodology": ["מדדים", "שעונים", "כלי", "שיטה", "מדה"],
    "parasha": ["אלוקים", "נפש", "בורא", "חי", "תודה"],
    "business": ["חזון", "פריצת דרך", "פרויקט", "זמן", "אנרגיה"],
}


def guess_category(title: str, body: str) -> str:
    text = f"{title} {body[:500]}"
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "coaching"


def blocks_to_markdown(blocks: list) -> str:
    parts = []
    for b in blocks:
        if b.get("type") == "image":
            alt = b.get("alt", "")
            src = b.get("src", "")
            parts.append(f"![{alt}]({src})")
        else:
            parts.append(b.get("text", ""))
    return "\n\n".join(parts)


def strip_md_for_meta(text: str) -> str:
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"\n+", " ", text)
    return text.strip()[:155]


def main():
    with open(ARTICLES_PATH, "r") as f:
        articles = json.load(f)

    client = httpx.Client(timeout=30)
    headers = {"X-Internal-Key": API_KEY, "Content-Type": "application/json"}

    migrated = 0
    skipped = 0

    for art in articles:
        slug = art["slug"]
        title = art["title"]

        if art.get("blocks"):
            content = blocks_to_markdown(art["blocks"])
        else:
            content = art.get("body", "")

        if not content.strip():
            print(f"  SKIP (empty): {slug}")
            skipped += 1
            continue

        excerpt = art.get("excerpt", "")
        if not excerpt:
            excerpt = strip_md_for_meta(content)

        category = guess_category(title, content)
        cover = art.get("featuredImage") or f"{BASE_URL}/api/public/blog-cover/{slug}"

        payload = {
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "category": category,
            "meta_title": title,
            "meta_description": strip_md_for_meta(content),
            "cover_image": cover,
            "status": "published",
            "language": "he",
        }

        resp = client.post(f"{API_URL}/api/admin/content/posts", json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  OK: {data['slug'][:50]}  ({data.get('word_count', '?')} words, {category})")
            migrated += 1
        else:
            print(f"  ERR ({resp.status_code}): {slug} — {resp.text[:100]}")
            skipped += 1

    print(f"\nDone: {migrated} migrated, {skipped} skipped")


if __name__ == "__main__":
    main()
