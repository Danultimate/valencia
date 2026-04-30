from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.schemas import AuctionListResponse, AuctionSchema
from storage.database import get_db
from storage.repository import get_active_auctions, get_current_bid

router = APIRouter()


@router.get("/items", response_model=AuctionListResponse)
def list_items(
    category: str | None = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Return only active auctions"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    auctions = get_active_auctions(db, category=category, limit=limit, offset=offset)

    items = []
    for auction in auctions:
        schema = AuctionSchema.model_validate(auction)
        schema.current_bid = get_current_bid(db, auction.id)
        items.append(schema)

    return AuctionListResponse(
        total=len(items),
        limit=limit,
        offset=offset,
        items=items,
    )
