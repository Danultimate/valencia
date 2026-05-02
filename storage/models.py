from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Auction(Base):
    __tablename__ = "auctions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    title_es: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128))
    location: Mapped[str | None] = mapped_column(String(128))
    appraisal_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    start_date: Mapped[datetime] = mapped_column(nullable=False)
    end_date: Mapped[datetime] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    opportunity_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.0"))
    last_scraped_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    bid_history: Mapped[list["BidHistory"]] = relationship(
        back_populates="auction", order_by="BidHistory.timestamp"
    )

    __table_args__ = (
        Index("idx_auctions_active_score", "is_active", "opportunity_score"),
    )


class BidHistory(Base):
    __tablename__ = "bid_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    auction_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("auctions.id"), nullable=False
    )
    bid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    auction: Mapped["Auction"] = relationship(back_populates="bid_history")

    __table_args__ = (Index("idx_bid_history_auction_id", "auction_id"),)
