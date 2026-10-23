import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from . import models
from .database import engine, Base
from .routers import auth, nodes, telemetry, alerts, system

logging.basicConfig(level=logging.INFO)

# Creates tables on startup if they don't exist yet (fine for a project; use
# Alembic migrations instead once this needs to survive schema changes in prod).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nodonomy Backend", version="1.0.0")

# Frontend runs on a different origin/port during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your actual frontend origin before deploying
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(nodes.router)
app.include_router(telemetry.router)
app.include_router(alerts.router)
app.include_router(system.router)


# ---------- Centralized error handling (Ch.7 of the Backend spec) ----------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Invalid request parameters",
            "detail": exc.errors(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.getLogger("nodonomy.errors").exception("Unhandled error on %s", request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/")
def root():
    return {"service": "Nodonomy Backend", "status": "running"}
