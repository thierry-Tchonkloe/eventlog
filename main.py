"""
main.py
-------
Run :
  uvicorn main:app --reload                    # développement
  uvicorn main:app --host 0.0.0.0 --port 8000  # production
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import init_db
from exceptions import register_exception_handlers
from routers import events, stats, debug


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="EventLog",
    description="Time-series event storage API",
    version="1.0.0",
    lifespan=lifespan,
)

# Handlers d'erreurs globaux (format {"error": ..., "code": ...})
register_exception_handlers(app)

# Routers
app.include_router(events.router)
app.include_router(stats.router)
app.include_router(debug.router)


# ---------------------------------------------------------------------------
# Health check minimal — utile pour les load balancers / CI
# ---------------------------------------------------------------------------
@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}