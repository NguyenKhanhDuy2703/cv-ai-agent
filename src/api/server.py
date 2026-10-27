import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from ..config import settings
from .routes import router as ai_router
from ..jobs.database import Database
from ..jobs.repository import JobRepository, JobConflict, JobNotFound

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Maximum request size is configurable via AI_MAX_BODY_SIZE (bytes).
MAX_BODY_SIZE = settings.ai_max_body_size

@asynccontextmanager
async def lifespan(app: FastAPI):
    database = Database(settings.ai_database_url)
    try:
        await database.check_ready()
        app.state.database = database
        app.state.job_repository = JobRepository(database, settings)
        yield
    finally:
        app.state.job_repository = None
        await database.close()


app = FastAPI(
    title="cv-ai-agent",
    description="Durable AI service for evidence-grounded canonical CV generation",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(JobConflict)
async def job_conflict(request: Request, error: JobConflict):
    return JSONResponse(status_code=409, content={"detail": str(error)})


@app.exception_handler(JobNotFound)
async def job_not_found(request: Request, error: JobNotFound):
    return JSONResponse(status_code=404, content={"detail": "Generation job not found"})

# CORS setup
origins = [origin.strip() for origin in settings.frontend_origin.split(",") if origin.strip()]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def limit_body_and_log_access(request: Request, call_next):
    # Check Content-Length header to prevent oversized payloads
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": f"Request body too large. Maximum allowed is {MAX_BODY_SIZE} bytes."},
        )

    start_time = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start_time

    # Safe log: never log body or candidate PII, only path, method, status, duration
    logger.info(
        "HTTP %s %s status=%d duration=%.3fs",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response


app.include_router(ai_router)


@app.get("/", include_in_schema=False)
async def root_redirect():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    return {"status": "ok", "provider": settings.ai_provider}


@app.get("/health/live")
async def health_live():
    return {"status": "live"}


@app.get("/health/ready")
async def health_ready(request: Request):
    database = getattr(request.app.state, "database", None)
    try:
        if database is None:
            raise RuntimeError("Database is not initialized")
        await database.check_ready()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready", "provider": settings.ai_provider}
