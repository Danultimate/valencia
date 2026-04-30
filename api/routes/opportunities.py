from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.schemas import AuctionSchema, OpportunitiesResponse
from storage.database import get_db
from storage.repository import get_current_bid, get_opportunities

router = APIRouter()


@router.get("/opportunities", response_model=OpportunitiesResponse)
def list_opportunities(
    min_score: float = Query(0.0, ge=0.0, description="Minimum opportunity score threshold"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    auctions = get_opportunities(db, min_score=min_score, limit=limit)

    items = []
    for auction in auctions:
        schema = AuctionSchema.model_validate(auction)
        schema.current_bid = get_current_bid(db, auction.id)
        items.append(schema)

    return OpportunitiesResponse(items=items, count=len(items))
