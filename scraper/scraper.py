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
PAGE_TIMEOUT_MS = 60_000
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
    """Two-level scrape: catalog → veiling event pages → individual kavel URLs."""
    # ------------------------------------------------------------------ #
    # Level 1: collect veiling event URLs from /nl/veilingen              #
    # ------------------------------------------------------------------ #
    VEILING_CATALOG = f"{TARGET_URL}/nl/veilingen"
    # Pattern for individual veiling event pages: /nl/veilingen/<numeric-id>
    VEILING_ID_RE = re.compile(r"^/nl/veilingen/(\d+)(/|$)")

    veiling_urls: list[str] = []
    current_url: str | None = VEILING_CATALOG

    while current_url:
        try:
            response = await page.goto(current_url, timeout=PAGE_TIMEOUT_MS, wait_until="networkidle")
            title = await page.title()
            status = response.status if response else "?"
            logger.info("Catalog page: %s (title: %r, status: %s)", current_url, title, status)
        except PWTimeout:
            logger.warning("Timeout on catalog page %s — stopping", current_url)
            break
        except Exception as exc:
            logger.warning("Error loading catalog %s: %s — stopping", current_url, exc)
            break

        all_anchors = await page.query_selector_all("a[href]")
        all_hrefs: list[str] = []
        page_new = 0

        for anchor in all_anchors:
            href = await anchor.get_attribute("href")
            if not href:
                continue
            all_hrefs.append(href)
            path = href if href.startswith("/") else ("/" + href.split(TARGET_URL, 1)[-1]) if TARGET_URL in href else None
            if path and VEILING_ID_RE.match(path):
                full = f"{TARGET_URL}{path}"
                if full not in veiling_urls:
                    veiling_urls.append(full)
                    page_new += 1

        logger.info("Catalog %s — %d new veiling links (total: %d)", current_url, page_new, len(veiling_urls))

        if not veiling_urls and not page_new:
            unique_hrefs = list(dict.fromkeys(all_hrefs))
            logger.warning("0 veiling URLs matched. Sample hrefs: %s", unique_hrefs[:30])

        # Pagination
        next_el = await page.query_selector(
            "a[rel='next'], a.next, .pagination .next a, "
            "a:has-text('Volgende'), a:has-text('Next'), a:has-text('>')"
        )
        if next_el:
            next_href = await next_el.get_attribute("href")
            current_url = (
                next_href if next_href and next_href.startswith("http")
                else f"{TARGET_URL}{next_href}" if next_href
                else None
            )
        else:
            current_url = None

        await asyncio.sleep(POLITE_DELAY)

    logger.info("Level-1 complete — %d veiling event pages found", len(veiling_urls))

    # ------------------------------------------------------------------ #
    # Level 2: visit each veiling event page and collect kavel/lot URLs   #
    # ------------------------------------------------------------------ #
    # Known patterns for individual lots on this site; we'll also log
    # unmatched hrefs from the first veiling page so we can refine.
    KAVEL_PATTERNS = [
        re.compile(r"/nl/kavels?/\d+"),
        re.compile(r"/nl/lot/\d+"),
        re.compile(r"/nl/item/\d+"),
        re.compile(r"/nl/object/\d+"),
        re.compile(r"/nl/veilingen/\d+/\w"),  # e.g. /nl/veilingen/8833/kavel-title
    ]

    item_urls: list[str] = []
    logged_sample = False

    for veiling_url in veiling_urls:
        await asyncio.sleep(POLITE_DELAY)
        try:
            await page.goto(veiling_url, timeout=PAGE_TIMEOUT_MS, wait_until="networkidle")
        except PWTimeout:
            logger.warning("Timeout on veiling page %s — skipping", veiling_url)
            continue
        except Exception as exc:
            logger.warning("Error loading veiling %s: %s — skipping", veiling_url, exc)
            continue

        anchors = await page.query_selector_all("a[href]")
        hrefs_on_page: list[str] = []
        page_new = 0

        for anchor in anchors:
            href = await anchor.get_attribute("href")
            if not href:
                continue
            hrefs_on_page.append(href)
            full = href if href.startswith("http") else f"{TARGET_URL}{href}"
            path = full.replace(TARGET_URL, "")
            if any(pat.search(path) for pat in KAVEL_PATTERNS) and full not in item_urls:
                item_urls.append(full)
                page_new += 1

        logger.info("Veiling %s — %d new kavel links (running total: %d)", veiling_url, page_new, len(item_urls))

        # Log a href sample from the first veiling page to help tune patterns
        if not logged_sample:
            logged_sample = True
            unique = list(dict.fromkeys(hrefs_on_page))
            logger.info("First veiling page href sample (for pattern tuning): %s", unique[:40])

    logger.info("Collected %d kavel URLs across %d veiling events", len(item_urls), len(veiling_urls))
    return item_urls


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
