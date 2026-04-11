import asyncio
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import api_router
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler


def run_migrations():
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        logger.error(f"Migration failed: {result.stderr}")
        raise RuntimeError(f"Migration failed: {result.stderr}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_migrations)

    await start_scheduler()
    logger.info("Scheduler started")

    yield

    await stop_scheduler()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="BangumiHelper API",
    description="A modern bangumi tracking and downloading assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
