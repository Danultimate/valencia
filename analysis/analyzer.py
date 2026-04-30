from datetime import datetime, timezone
from decimal import Decimal


def calculate_opportunity_score(
    appraisal_value: Decimal | float | None,
    estimated_value: Decimal | float | None,
    current_bid: Decimal | float,
    end_date: datetime,
) -> Decimal:
    """
    Score = (reference_value - current_bid) / (time_remaining_hours + 1)

    Higher score means a larger gap between value and current bid, expiring soon.
    Returns 0 when current bid exceeds reference value or no reference is available.
    """
    reference = float(appraisal_value or estimated_value or 0.0)
    bid = float(current_bid)

    if reference <= 0:
        return Decimal("0.0")

    now = datetime.now(timezone.utc)
    end = end_date if end_date.tzinfo else end_date.replace(tzinfo=timezone.utc)
    time_remaining_hours = max((end - now).total_seconds() / 3600, 0.0)

    raw_score = (reference - bid) / (time_remaining_hours + 1)
    return Decimal(str(round(max(raw_score, 0.0), 4)))
