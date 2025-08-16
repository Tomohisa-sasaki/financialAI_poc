
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.logging import init_logging
from core.config import get_settings
from storage.db import init_db
from services.company_service import ensure_seed
from .routers.health import router as health_router
from .routers.sources import router as sources_router
from .routers.analysis import router as analysis_router
from .routers.reports import router as reports_router
from .routers.companies import router as companies_router
from .routers.ai import router as ai_router

# Initialize infra bits at import time
init_logging()
init_db()
ensure_seed()

app = FastAPI(title="Financial AI API", version="1.0.0")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router)
app.include_router(sources_router)
app.include_router(analysis_router)
app.include_router(reports_router)
app.include_router(companies_router)
app.include_router(ai_router)
