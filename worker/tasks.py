import asyncio
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

from celery import Celery
from celery.schedules import crontab

from analysis.analyzer import calculate_opportunity_score
from analysis import model as ml_model
from scraper.scraper import scrape_all
from storage.database import SessionLocal, init_db
from storage.repository import (
    append_bid,
    get_completed_auctions_count,
    get_current_bid,
    get_training_data,
    update_scores,
    upsert_auction,
)

logger = logging.getLogger(__name__)

BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
SCRAPE_INTERVAL_SECONDS = int(os.environ.get("SCRAPE_INTERVAL_SECONDS", "5400"))

app = Celery("valencia_auctions", broker=BROKER_URL, backend=RESULT_BACKEND)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_max_tasks_per_child=50,
    task_acks_late=True,
)

app.conf.beat_schedule = {
    "scrape-auctions": {
        "task": "worker.tasks.run_scrape_pipeline",
        "schedule": SCRAPE_INTERVAL_SECONDS,
    },
}


@app.on_after_configure.connect
def setup_db(sender, **kwargs):
    init_db()


# --------------------------------------------------------------------------- #
# Main pipeline task                                                           #
# --------------------------------------------------------------------------- #

@app.task(bind=True, max_retries=3, default_retry_delay=120, name="worker.tasks.run_scrape_pipeline")
def run_scrape_pipeline(self):
    logger.info("Scrape pipeline started at %s", datetime.now(timezone.utc).isoformat())

    try:
        results = asyncio.run(scrape_all())
    except Exception as exc:
        logger.error("Scraper failed: %s", exc)
        raise self.retry(exc=exc)

    if not results:
        logger.warning("Scraper returned 0 items")
        return {"scraped": 0, "scored": 0}

    db = SessionLocal()
    scored = 0
    newly_completed = 0

    try:
        for item, snapshot in results:
            # Persist auction (upsert)
            auction_data = {
                "id": item.id,
                "title": item.title,
                "category": item.category,
                "location": item.location,
                "url": item.url,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "appraisal_value": Decimal(str(item.appraisal_value)) if item.appraisal_value else None,
                # Items scraped from the live catalog are active by definition.
                # Only mark inactive if end_date was actually parsed (not the now() fallback).
                "is_active": True,
            }
            auction = upsert_auction(db, auction_data)

            # Track newly completed auctions for retraining decision
            if not auction.is_active:
                newly_completed += 1

            # Persist bid snapshot
            append_bid(db, item.id, Decimal(str(snapshot.bid_amount)))

            # Compute estimated value via RF if appraisal missing
            estimated_value = None
            if item.appraisal_value is None:
                current_bid = get_current_bid(db, item.id)
                bid_count = len(auction.bid_history) if auction.bid_history else 0
                days_active = max(
                    (item.end_date - item.start_date).total_seconds() / 86400, 0
                )
                predicted = ml_model.predict_value(
                    category=item.category or "unknown",
                    days_active=days_active,
                    num_bids=bid_count,
                    starting_bid=float(current_bid or 0),
                )
                if predicted is not None:
                    estimated_value = Decimal(str(round(predicted, 2)))

            # Compute and persist opportunity score
            score = calculate_opportunity_score(
                appraisal_value=item.appraisal_value,
                estimated_value=estimated_value,
                current_bid=snapshot.bid_amount,
                end_date=item.end_date,
            )
            update_scores(db, item.id, score, estimated_value)
            scored += 1

        # Retrain ML model if enough new completed auctions
        if ml_model.should_retrain(newly_completed):
            logger.info("Retraining model — %d newly completed auctions", newly_completed)
            training_data = get_training_data(db)
            ml_model.train(training_data)

    except Exception as exc:
        logger.error("Pipeline DB/analysis error: %s", exc)
        db.rollback()
        raise
    finally:
        db.close()

    logger.info("Pipeline complete — scraped: %d, scored: %d", len(results), scored)
    return {"scraped": len(results), "scored": scored}
