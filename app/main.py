from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import audit as audit_api

# API routers
from app.api import auth as auth_api
from app.api import catalog as catalog_api
from app.api import comments as comments_api
from app.api import decisions as decisions_api
from app.api import fields as fields_api
from app.api import reminders as reminders_api
from app.api import requests as requests_api
from app.api import revisions as revisions_api
from app.api import users as users_api
from app.config import settings
from app.core.errors import generic_exception_handler
from app.scheduler import start_scheduler, stop_scheduler

# Web routers
from app.web import admin_pages, auth_pages, catalog_pages, dashboard, partials, request_pages

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="SysIntro API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Error handler
app.add_exception_handler(Exception, generic_exception_handler)

# CORS — tightly scoped: only configured origins, only methods/headers we actually use
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "HX-Request", "HX-Target", "HX-Trigger"],
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# API routes (all under /api/v1)
API_PREFIX = "/api/v1"
app.include_router(auth_api.router, prefix=API_PREFIX)
app.include_router(users_api.router, prefix=API_PREFIX)
app.include_router(fields_api.router, prefix=API_PREFIX)
app.include_router(requests_api.router, prefix=API_PREFIX)
app.include_router(decisions_api.router, prefix=API_PREFIX)
app.include_router(comments_api.router, prefix=API_PREFIX)
app.include_router(revisions_api.router, prefix=API_PREFIX)
app.include_router(catalog_api.router, prefix=API_PREFIX)
app.include_router(audit_api.router, prefix=API_PREFIX)
app.include_router(reminders_api.router, prefix=API_PREFIX)

# Web routes
app.include_router(auth_pages.router)
app.include_router(dashboard.router)
app.include_router(request_pages.router)
app.include_router(catalog_pages.router)
app.include_router(admin_pages.router)
app.include_router(partials.router)
