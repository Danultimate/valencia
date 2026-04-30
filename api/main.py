import os

import redis as redis_client
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import items, opportunities, scrape
from api.schemas import HealthResponse
from storage.database import check_db_health, init_db, SessionLocal
from storage.repository import get_last_scraped_at

app = FastAPI(
    title="Valencia Auctions API",
    description="Dutch government auction tracker with ML-driven Opportunity Scores",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(items.router)
app.include_router(opportunities.router)
app.include_router(scrape.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
def health_check():
    db_status = "ok" if check_db_health() else "error"

    redis_status = "error"
    try:
        r = redis_client.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
        r.ping()
        redis_status = "ok"
    except Exception:
        pass

    last_scraped_at = None
    try:
        db = SessionLocal()
        last_scraped_at = get_last_scraped_at(db)
        db.close()
    except Exception:
        pass

    return HealthResponse(
        db=db_status,
        redis=redis_status,
        last_scraped_at=last_scraped_at,
    )
