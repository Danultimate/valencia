import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

TARGET_URL = os.environ.get("TARGET_URL", "https://www.onlineveilingmeester.nl")
POLITE_DELAY = float(os.environ.get("SCRAPE_POLITE_DELAY_SECONDS", "2"))
PAGE_TIMEOUT_MS = 30_000
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class AuctionItem:
    id: str
    title: str
    category: str | None
    location: str | None
    url: str
    start_date: datetime
    end_date: datetime
    appraisal_value: float | None


@dataclass
class BidSnapshot:
    auction_id: str
    bid_amount: float
    timestamp: datetime


# --------------------------------------------------------------------------- #
# Parsing helpers                                                              #
# --------------------------------------------------------------------------- #

def _parse_price(raw: str | None) -> float | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d,.]", "", raw).replace(",", ".")
    # handle European "1.234,56" format
    if cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "", cleaned.count(".") - 1)
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_dutch_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    DUTCH_MONTHS = {
        "jan": 1, "feb": 2, "mrt": 3, "apr": 4, "mei": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12,
    }
    raw = raw.strip().lower()
    for nl, num in DUTCH_MONTHS.items():
        raw = raw.replace(nl, str(num).zfill(2))
    formats = [
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%d %m %Y %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%d-%m-%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _extract_auction_id(url: str) -> str:
    # Extract numeric or slug ID from URL path
    match = re.search(r"/(?:lot|kavel|item|veiling)/([^/?#]+)", url, re.IGNORECASE)
    if match:
        return match.group(1)
    # Fallback: last non-empty path segment
    parts = [p for p in url.rstrip("/").split("/") if p]
    return parts[-1] if parts else url


# --------------------------------------------------------------------------- #
# Page scrapers                                                                #
# --------------------------------------------------------------------------- #

async def _scrape_item_page(page: Page, url: str) -> tuple[AuctionItem, BidSnapshot] | None:
    try:
        await page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
    except PWTimeout:
        logger.warning("Timeout loading %s — skipping", url)
        return None
    except Exception as exc:
        logger.warning("Error loading %s: %s — skipping", url, exc)
        return None

    auction_id = _extract_auction_id(url)

    async def text(selector: str) -> str | None:
        try:
            el = await page.query_selector(selector)
            return (await el.inner_text()).strip() if el else None
        except Exception:
            return None

    title = (
        await text("h1")
        or await text(".lot-title")
        or await text(".auction-title")
        or "Onbekend"
    )

    # Current bid — try multiple common selectors
    bid_raw = (
        await text(".current-bid")
        or await text(".bid-amount")
        or await text("[data-current-bid]")
        or await text(".price")
    )
    current_bid = _parse_price(bid_raw) or 0.0

    # End date
    end_raw = (
        await text(".end-date")
        or await text(".closing-time")
        or await text("[data-end-time]")
        or await text(".auction-end")
    )
    end_date = _parse_dutch_datetime(end_raw) or datetime.now(timezone.utc)

    # Start date (best effort)
    start_raw = await text(".start-date") or await text("[data-start-time]")
    start_date = _parse_dutch_datetime(start_raw) or datetime.now(timezone.utc)

    # Category
    category = (
        await text(".category")
        or await text(".breadcrumb li:nth-child(2)")
        or await text("[data-category]")
    )

    # Location
    location = await text(".location") or await text("[data-location]")

    # Appraisal value (taxatiewaarde / schattingswaarde)
    appraisal_raw = (
        await text(".appraisal-value")
        or await text(".taxatiewaarde")
        or await text("[data-appraisal]")
    )
    appraisal_value = _parse_price(appraisal_raw)

    item = AuctionItem(
        id=auction_id,
        title=title,
        category=category,
        location=location,
        url=url,
        start_date=start_date,
        end_date=end_date,
        appraisal_value=appraisal_value,
    )
    snapshot = BidSnapshot(
        auction_id=auction_id,
        bid_amount=current_bid,
        timestamp=datetime.now(timezone.utc),
    )
    return item, snapshot


async def _collect_item_urls(page: Page) -> list[str]:
    """Navigate catalog pages and collect all auction item URLs."""
    urls: list[str] = []
    current_url = f"{TARGET_URL}/veilingen"

    while current_url:
        try:
            await page.goto(current_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
        except PWTimeout:
            logger.warning("Timeout on catalog page %s — stopping pagination", current_url)
            break

        # Collect links matching auction item patterns
        anchors = await page.query_selector_all(
            "a[href*='/lot/'], a[href*='/kavel/'], a[href*='/item/'], "
            "a.lot-link, a.auction-item-link, .lot-card a, .auction-card a"
        )
        for anchor in anchors:
            href = await anchor.get_attribute("href")
            if href:
                full = href if href.startswith("http") else f"{TARGET_URL}{href}"
                if full not in urls:
                    urls.append(full)

        # Pagination — look for "next" link
        next_el = await page.query_selector(
            "a[rel='next'], a.next, .pagination .next a, "
            "a:has-text('Volgende'), a:has-text('>')"
        )
        if next_el:
            next_href = await next_el.get_attribute("href")
            current_url = (
                next_href
                if next_href and next_href.startswith("http")
                else f"{TARGET_URL}{next_href}"
                if next_href
                else None
            )
        else:
            current_url = None

        await asyncio.sleep(POLITE_DELAY)

    logger.info("Collected %d auction URLs", len(urls))
    return urls


# --------------------------------------------------------------------------- #
# Public entry point                                                           #
# --------------------------------------------------------------------------- #

async def scrape_all() -> list[tuple[AuctionItem, BidSnapshot]]:
    results: list[tuple[AuctionItem, BidSnapshot]] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        urls = await _collect_item_urls(page)

        for url in urls:
            await asyncio.sleep(POLITE_DELAY)
            try:
                result = await _scrape_item_page(page, url)
                if result:
                    results.append(result)
                    logger.debug("Scraped %s — bid: %.2f", result[0].id, result[1].bid_amount)
            except Exception as exc:
                logger.error("Unhandled error scraping %s: %s", url, exc)

        await browser.close()

    logger.info("Scrape complete — %d items collected", len(results))
    return results
