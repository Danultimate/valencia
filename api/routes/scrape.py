import os

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from api.schemas import ScrapeTaskResponse
from worker.tasks import run_scrape_pipeline

router = APIRouter()

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)
_SCRAPE_API_KEY = os.environ.get("SCRAPE_API_KEY", "")


def _verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    if not _SCRAPE_API_KEY or api_key != _SCRAPE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return api_key


@router.post("/scrape/trigger", response_model=ScrapeTaskResponse, status_code=202)
def trigger_scrape(api_key: str = Depends(_verify_api_key)):
    task = run_scrape_pipeline.delay()
    return ScrapeTaskResponse(task_id=task.id, status="queued")
