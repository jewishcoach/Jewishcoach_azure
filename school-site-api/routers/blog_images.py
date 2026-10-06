"""Blog image generation — gpt-image-1 via Azure OpenAI + Blob Storage."""

from __future__ import annotations

import io
import os
import re
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_admin
import db

router = APIRouter(prefix="/api/admin/content", tags=["images"])

AZURE_IMAGES_ENDPOINT = os.environ.get("AZURE_IMAGES_ENDPOINT", "")
AZURE_IMAGES_KEY = os.environ.get("AZURE_IMAGES_KEY", "")
AZURE_STORAGE_ACCOUNT = os.environ.get("AZURE_STORAGE_ACCOUNT", "bsdschoolmedia")
AZURE_STORAGE_KEY = os.environ.get("AZURE_STORAGE_KEY", "")
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER", "blog-images")
BASE_URL = os.environ.get("BASE_URL", "https://www.bsdcoaching.co.il")

_COMPOSITIONS = [
    "bird's-eye view, serene atmosphere",
    "close-up on hands, warm lighting",
    "wide landscape with depth",
    "centered subject with ambient glow",
    "soft golden hour lighting",
    "minimalist with ample negative space",
    "gentle bokeh background",
]


def _upload_to_blob(data: bytes, filename: str) -> str | None:
    if not AZURE_STORAGE_KEY:
        return None
    from azure.storage.blob import BlobServiceClient, ContentSettings
    service = BlobServiceClient(
        account_url=f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=AZURE_STORAGE_KEY,
    )
    blob = service.get_blob_client(container=AZURE_STORAGE_CONTAINER, blob=filename)
    blob.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type="image/png"))
    return f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER}/{filename}"


def _generate_image(prompt: str, filename: str, size: str = "1536x1024") -> str | None:
    if not AZURE_IMAGES_KEY:
        return None
    from openai import AzureOpenAI
    import base64 as _b64

    client = AzureOpenAI(
        api_key=AZURE_IMAGES_KEY,
        azure_endpoint=AZURE_IMAGES_ENDPOINT,
        api_version="2024-08-01-preview",
    )

    result = client.images.generate(model="gpt-image-1", prompt=prompt, n=1, size=size)

    img_data = None
    if result.data[0].url:
        import httpx
        img_data = httpx.get(result.data[0].url).content
    elif result.data[0].b64_json:
        img_data = _b64.b64decode(result.data[0].b64_json)

    if img_data:
        from PIL import Image
        img = Image.open(io.BytesIO(img_data))
        clean = io.BytesIO()
        img.save(clean, format="PNG")
        return _upload_to_blob(clean.getvalue(), filename)
    return None


def _safe_filename(text: str) -> str:
    """Generate ASCII-safe filename from any text using hash."""
    import hashlib
    h = hashlib.md5(text.encode()).hexdigest()[:12]
    return h


def generate_cover_image(keyword: str, title: str) -> str | None:
    day = date.today().timetuple().tm_yday
    composition = _COMPOSITIONS[day % len(_COMPOSITIONS)]

    prompt = f"""Create a premium blog cover PHOTOGRAPH about "{keyword}".

COLOR TONES: warm golden hour, soft natural light, muted earth tones, Mediterranean warmth. Deep shadows with warm highlights.
STYLE: Professional editorial photography — real textures, natural depth of field, cinematic feel. Like a premium lifestyle magazine cover photo. Warm, authentic, thoughtful.
COMPOSITION: {composition}

Scene based on topic:
- coaching/personal growth → person walking on a path at golden hour, back to camera, wide landscape
- Jewish wisdom → old leather-bound books on wooden table, soft candlelight, vintage study room
- couples/relationships → two people silhouetted against warm light, hands almost touching, intimate moment
- crisis/midlife → person standing at crossroads, mountain dawn, dramatic sky breaking through clouds
- business/leadership → boardroom with warm light, compass on map, person looking at city from rooftop
- vision/goals → open road leading to horizon, ladder against sky, door opening to bright garden
- General → Mediterranean landscape with olive tree, stone path, warm golden hour lighting

MUST: No text, no words, no letters, no logos, no numbers in the image.
MUST: Photographic style — real camera look, natural lighting, depth of field, film grain texture.
GOAL: Should feel like a premium Jewish lifestyle magazine photograph — warm, deep, authentic, cinematic."""

    fname = f"blog-{_safe_filename(keyword)}-{uuid.uuid4().hex[:6]}.png"
    return _generate_image(prompt, fname)


def generate_inline_image(keyword: str, context: str) -> str | None:
    prompt = f"""Create a supporting ILLUSTRATION for a Hebrew article about "{keyword}".
Context in the article: {context[:200]}

COLOR PALETTE: muted sage green, warm gold, deep teal, cream, olive tones.
STYLE: Hand-drawn editorial illustration — NOT a photograph. Flat colors, subtle texture, paper-cut or woodcut feel. One key visual metaphor.
MUST: No text, no words, no letters.
Keep it simple, warm, and evocative — like a page from an illustrated Jewish art book."""

    fname = f"inline-{_safe_filename(keyword)}-{uuid.uuid4().hex[:6]}.png"
    return _generate_image(prompt, fname, size="1024x1024")


class GenerateImageRequest(BaseModel):
    slug: str


@router.post("/images/generate-cover")
async def generate_cover_for_post(body: GenerateImageRequest, _=Depends(require_admin)):
    post = db.get_post(body.slug)
    if not post:
        raise HTTPException(404, "Post not found")

    url = generate_cover_image(post.keyword or post.title, post.title)
    if not url:
        raise HTTPException(502, "Image generation failed — check AZURE_IMAGES_KEY")

    db.update_post(body.slug, {"cover_image": url})
    return {"slug": body.slug, "cover_image": url}


@router.post("/images/generate-all")
async def generate_images_for_post(body: GenerateImageRequest, _=Depends(require_admin)):
    """Generate cover + 1 inline image, inject inline image into markdown content."""
    post = db.get_post(body.slug)
    if not post:
        raise HTTPException(404, "Post not found")

    keyword = post.keyword or post.title
    results = {"slug": body.slug, "cover": None, "inline": None}

    cover_url = generate_cover_image(keyword, post.title)
    if cover_url:
        results["cover"] = cover_url
        db.update_post(body.slug, {"cover_image": cover_url})

    # Find a good place to insert inline image (after first ## heading)
    lines = post.content.split("\n")
    h2_count = 0
    insert_idx = None
    context = ""
    for i, line in enumerate(lines):
        if line.startswith("## "):
            h2_count += 1
            if h2_count == 2:
                insert_idx = i + 1
                context = line
                break

    if insert_idx:
        inline_url = generate_inline_image(keyword, context)
        if inline_url:
            results["inline"] = inline_url
            lines.insert(insert_idx, f"\n![{keyword}]({inline_url})\n")
            db.update_post(body.slug, {"content": "\n".join(lines)})

    return results
