from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

import db as blog_db
from routers.blog import router as blog_admin_router, public_router as blog_public_router
from routers.blog_render import router as blog_render_router
from routers.blog_cover import router as blog_cover_router
from routers.blog_generate import router as blog_generate_router
from routers.blog_images import router as blog_images_router
from routers.subscribe import router as subscribe_router
from routers.seo import router as seo_router
from routers.rankita import router as rankita_router

@asynccontextmanager
async def lifespan(app):
    blog_db.init_db()
    yield

app = FastAPI(title="BSD School Blog API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(blog_admin_router)
app.include_router(blog_public_router)
app.include_router(blog_render_router)
app.include_router(blog_cover_router)
app.include_router(blog_generate_router)
app.include_router(blog_images_router)
app.include_router(subscribe_router)
app.include_router(seo_router)
app.include_router(rankita_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
