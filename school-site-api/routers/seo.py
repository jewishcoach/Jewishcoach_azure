from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import Response

import db

router = APIRouter(prefix="/api", tags=["seo"])

BASE_URL = os.environ.get("BASE_URL", "https://www.bsdcoaching.co.il")


@router.get("/robots.txt")
async def robots_txt():
    content = f"""User-agent: *
Allow: /
Allow: /blog/
Allow: /bsd-ai
Allow: /about
Allow: /contact
Allow: /programs/
Allow: /book
Allow: /testimonials

Disallow: /api/

Sitemap: {BASE_URL}/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml")
async def sitemap_xml():
    posts = db.list_posts(status="published")
    now = datetime.utcnow().strftime("%Y-%m-%d")

    static_pages = [
        {"loc": "", "priority": "1.0", "changefreq": "weekly"},
        {"loc": "/blog", "priority": "0.8", "changefreq": "daily"},
        {"loc": "/bsd-ai", "priority": "0.9", "changefreq": "monthly"},
        {"loc": "/about", "priority": "0.6", "changefreq": "monthly"},
        {"loc": "/contact", "priority": "0.5", "changefreq": "monthly"},
        {"loc": "/programs/personal", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/programs/find-coach", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/programs/certified-coaches", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/book", "priority": "0.6", "changefreq": "monthly"},
        {"loc": "/testimonials", "priority": "0.6", "changefreq": "monthly"},
    ]

    urls = []
    for page in static_pages:
        urls.append(f"""  <url>
    <loc>{BASE_URL}{page['loc']}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>{page['changefreq']}</changefreq>
    <priority>{page['priority']}</priority>
  </url>""")

    for post in posts:
        lastmod = (post.updated_at or post.published_at or post.created_at)[:10]
        urls.append(f"""  <url>
    <loc>{BASE_URL}/blog/{post.slug}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
    return Response(content=xml, media_type="application/xml")


@router.get("/video-sitemap.xml")
async def video_sitemap_xml():
    posts = db.list_posts(status="published")
    video_posts = [p for p in posts if p.video_url]

    entries = []
    for post in video_posts:
        entries.append(f"""  <url>
    <loc>{BASE_URL}/blog/{post.slug}</loc>
    <video:video>
      <video:thumbnail_loc>{post.cover_image or f"{BASE_URL}/api/public/blog-cover/{post.slug}"}</video:thumbnail_loc>
      <video:title>{post.title}</video:title>
      <video:description>{post.meta_description or post.excerpt or ""}</video:description>
      <video:content_loc>{post.video_url}</video:content_loc>
    </video:video>
  </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">
{chr(10).join(entries)}
</urlset>"""
    return Response(content=xml, media_type="application/xml")
