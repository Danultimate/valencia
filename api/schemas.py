from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


class BidHistorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auction_id: str
    bid_amount: float
    timestamp: datetime


class AuctionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str | None
    location: str | None
    url: str
    start_date: datetime
    end_date: datetime
    appraisal_value: float | None
    estimated_value: float | None
    is_active: bool
    opportunity_score: float
    last_scraped_at: datetime | None
    created_at: datetime
    current_bid: float | None = None

    @computed_field
    @property
    def time_remaining_hours(self) -> float:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        end = self.end_date if self.end_date.tzinfo else self.end_date.replace(tzinfo=timezone.utc)
        return max((end - now).total_seconds() / 3600, 0.0)


class AuctionListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AuctionSchema]


class OpportunitiesResponse(BaseModel):
    items: list[AuctionSchema]
    count: int


class ScrapeTaskResponse(BaseModel):
    task_id: str
    status: str


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    last_scraped_at: datetime | None
    active_auctions: int
