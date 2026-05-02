from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from storage.models import Auction, BidHistory


# --------------------------------------------------------------------------- #
# Auction writes                                                               #
# --------------------------------------------------------------------------- #

def upsert_auction(db: Session, data: dict) -> Auction:
    stmt = (
        insert(Auction)
        .values(**data)
        .on_conflict_do_update(
            index_elements=["id"],
            set_={
                "title": data["title"],
                "category": data.get("category"),
                "location": data.get("location"),
                "appraisal_value": data.get("appraisal_value"),
                "end_date": data["end_date"],
                "is_active": data.get("is_active", True),
                "last_scraped_at": datetime.now(timezone.utc),
            },
        )
    )
    db.execute(stmt)
    db.commit()
    return db.get(Auction, data["id"])


def update_scores(
    db: Session,
    auction_id: str,
    opportunity_score: Decimal,
    estimated_value: Decimal | None = None,
) -> None:
    auction = db.get(Auction, auction_id)
    if auction is None:
        return
    auction.opportunity_score = opportunity_score
    if estimated_value is not None:
        auction.estimated_value = estimated_value
    db.commit()


def update_title_es(db: Session, auction_id: str, title_es: str) -> None:
    auction = db.get(Auction, auction_id)
    if auction:
        auction.title_es = title_es
        db.commit()


def mark_inactive(db: Session, auction_id: str) -> None:
    auction = db.get(Auction, auction_id)
    if auction:
        auction.is_active = False
        db.commit()


# --------------------------------------------------------------------------- #
# Bid history writes                                                           #
# --------------------------------------------------------------------------- #

def append_bid(db: Session, auction_id: str, bid_amount: Decimal) -> BidHistory:
    bid = BidHistory(
        auction_id=auction_id,
        bid_amount=bid_amount,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid


# --------------------------------------------------------------------------- #
# Auction reads                                                                #
# --------------------------------------------------------------------------- #

def get_active_auctions(
    db: Session,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Auction]:
    stmt = select(Auction).where(Auction.is_active == True)
    if category:
        stmt = stmt.where(Auction.category == category)
    stmt = stmt.order_by(Auction.end_date).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def count_active_auctions(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Auction).where(Auction.is_active == True)) or 0


def get_opportunities(
    db: Session,
    min_score: float = 0.0,
    limit: int = 20,
) -> list[Auction]:
    stmt = (
        select(Auction)
        .where(Auction.is_active == True)
        .where(Auction.opportunity_score >= Decimal(str(min_score)))
        .order_by(Auction.opportunity_score.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def get_current_bid(db: Session, auction_id: str) -> Decimal | None:
    stmt = (
        select(BidHistory.bid_amount)
        .where(BidHistory.auction_id == auction_id)
        .order_by(BidHistory.timestamp.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def get_last_scraped_at(db: Session) -> datetime | None:
    stmt = select(func.max(Auction.last_scraped_at))
    return db.scalar(stmt)


# --------------------------------------------------------------------------- #
# ML training reads                                                            #
# --------------------------------------------------------------------------- #

def get_completed_auctions_count(db: Session) -> int:
    stmt = select(func.count()).select_from(Auction).where(Auction.is_active == False)
    return db.scalar(stmt) or 0


def get_training_data(db: Session) -> list[dict]:
    """
    Returns completed auctions with their final hammer price and feature data
    for RandomForest training.
    """
    completed = db.scalars(
        select(Auction).where(Auction.is_active == False)
    ).all()

    rows = []
    for auction in completed:
        final_bid = get_current_bid(db, auction.id)
        if final_bid is None:
            continue
        bid_count_stmt = (
            select(func.count())
            .select_from(BidHistory)
            .where(BidHistory.auction_id == auction.id)
        )
        bid_count = db.scalar(bid_count_stmt) or 0
        days_active = max(
            (auction.end_date - auction.start_date).total_seconds() / 86400, 0
        )
        rows.append(
            {
                "auction_id": auction.id,
                "category": auction.category or "unknown",
                "days_active": days_active,
                "num_bids": bid_count,
                "starting_bid": float(
                    db.scalar(
                        select(BidHistory.bid_amount)
                        .where(BidHistory.auction_id == auction.id)
                        .order_by(BidHistory.timestamp)
                        .limit(1)
                    )
                    or 0
                ),
                "final_price": float(final_bid),
            }
        )
    return rows
