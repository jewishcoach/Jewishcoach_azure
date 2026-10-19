from __future__ import annotations

from datetime import datetime, date
from typing import Literal

from pydantic import BaseModel, Field


class BlogPost(BaseModel):
    slug: str
    title: str
    content: str = ""
    excerpt: str = ""
    category: str = "coaching"
    keyword: str = ""
    meta_title: str | None = None
    meta_description: str | None = None
    cover_image: str | None = None
    video_url: str | None = None
    author_name: str = "בית הספר לאימון יהודי BSD"
    author_role: str = ""
    word_count: int = 0
    language: str = "he"
    status: Literal["draft", "scheduled", "published"] = "draft"
    published_at: str | None = None
    scheduled_date: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class BlogPostCreate(BaseModel):
    title: str
    content: str = ""
    excerpt: str = ""
    category: str = "coaching"
    keyword: str = ""
    meta_title: str | None = None
    meta_description: str | None = None
    cover_image: str | None = None
    video_url: str | None = None
    author_name: str = "בית הספר לאימון יהודי BSD"
    language: str = "he"
    status: Literal["draft", "scheduled", "published"] = "draft"
    scheduled_date: str | None = None


class BlogPostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    excerpt: str | None = None
    category: str | None = None
    keyword: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    cover_image: str | None = None
    video_url: str | None = None
    author_name: str | None = None
    language: str | None = None
    status: Literal["draft", "scheduled", "published"] | None = None
    scheduled_date: str | None = None
