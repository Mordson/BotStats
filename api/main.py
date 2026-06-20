"""
Aplikacja FastAPI - warstwa API udostępniająca dane dla dashboardu.

Uruchomienie (dev):
    uvicorn api.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from core.database import init_db

# WAŻNE: rejestracja modeli na Base.metadata przed init_db()
from core import models  # noqa: F401

from api.routers import stats, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Discord Activity Dashboard API", lifespan=lifespan)

origins = [settings.cors_origins] if settings.cors_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(stats.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
