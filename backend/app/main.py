import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import traceback
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import init_db
from app.services.scheduler import start_scheduler, stop_scheduler
from app.api import auth, sites, telegram, billing
from app.core.config import settings
import os

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up SiteWatcher...")
    await init_db()
    start_scheduler()
    yield
    logger.info("Shutting down...")
    stop_scheduler()


IS_PRODUCTION = os.getenv("ENV") == "production"

app = FastAPI(
    title="SiteWatcher API",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(sites.router, prefix="/api")
app.include_router(telegram.router, prefix="/api")
app.include_router(billing.router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow()}

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": traceback.format_exc()}
    )