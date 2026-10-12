"""Turns raw search results into demand, supply and opportunity scores.

All scores run 0-100. They are rules of thumb meant to compare keywords
against each other, not exact predictions of what you will sell.
"""

from __future__ import annotations

import math
from statistics import median

from .models import KeywordReport, Product, SearchResult

# How many of the top organic (non-ad) listings count as "page one".
TOP_N = 10
# A listing with this many reviews is an established competitor.
STRONG_REVIEWS = 1000
# A listing below this many reviews, or rated under BEATABLE_RATING,
# is one a new seller can realistically outrank.
BEATABLE_REVIEWS = 200
BEATABLE_RATING = 4.0


def _log_scale(value: float, low: float, high: float) -> float:
    """Map value onto 0..1 on a log scale, where low -> 0 and high -> 1."""
    if value <= 0:
        return 0.0
    pos = (math.log10(value) - math.log10(low)) / (math.log10(high) - math.log10(low))
    return min(1.0, max(0.0, pos))


def _linear_scale(value: float, low: float, high: float) -> float:
    return min(1.0, max(0.0, (value - low) / (high - low)))


def _median_or_none(values: list[float]) -> float | None:
    return median(values) if values else None


def analyze(result: SearchResult) -> KeywordReport:
    organic = [p for p in result.products if not p.sponsored]
    top = organic[:TOP_N]
    notes: list[str] = []

    # ---- Demand -----------------------------------------------------------
    prices = [p.price for p in top if p.price]
    median_price = _median_or_none(prices)

    sales_known = [p.monthly_sales for p in top if p.monthly_sales is not None]
    est_units = sum(sales_known) if sales_known else None
    est_revenue = (
        round(est_units * median_price) if est_units is not None and median_price else None
    )
    median_reviews_top = _median_or_none([p.reviews for p in top])

    if est_units is not None:
        # 300 units/month across page one is a thin market; 30,000 is a big one.
        demand_score = _log_scale(est_units, 300, 30_000)
        if len(sales_known) < len(top):
            notes.append(
                f"Sales figures were available for only {len(sales_known)} of the top "
                f"{len(top)} listings, so demand is probably understated."
            )
    elif median_reviews_top is not None:
        # No sales data: fall back to reviews, which build up roughly in
        # proportion to lifetime sales.
        demand_score = _log_scale(median_reviews_top, 50, 20_000)
        notes.append("No sales data available; demand is estimated from review counts only.")
    else:
        demand_score = 0.0
        notes.append("No listings found, so demand could not be measured.")

    demand = {
        "est_monthly_units_top10": est_units,
        "est_monthly_revenue_top10": est_revenue,
        "median_price": round(median_price, 2) if median_price else None,
        "median_reviews_top10": median_reviews_top,
    }

    # ---- Supply / competition --------------------------------------------
    n = len(top) or 1
    strong = sum(1 for p in top if p.reviews >= STRONG_REVIEWS)
    beatable = sum(
        1
        for p in top
        if p.reviews < BEATABLE_REVIEWS or (p.rating is not None and p.rating < BEATABLE_RATING)
    )
    top_reviews = sorted((p.reviews for p in top), reverse=True)
    total_reviews = sum(top_reviews)
    concentration = sum(top_reviews[:3]) / total_reviews if total_reviews else 0.0
    ratings = [p.rating for p in top if p.rating is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else None
    sponsored_share = (
        sum(1 for p in result.products if p.sponsored) / len(result.products)
        if result.products
        else 0.0
    )
    brands = {p.brand.strip().lower() for p in top if p.brand}

    competition = (
        0.35 * (strong / n)
        + 0.20 * sponsored_share / 0.5  # half the page being ads is very heavy
        + 0.15 * (_linear_scale(avg_rating, 4.0, 4.7) if avg_rating else 0.5)
        + 0.15 * concentration
        + 0.15 * (_log_scale(result.total_results, 1_000, 100_000) if result.total_results else 0.5)
    )
    competition = min(1.0, competition)

    supply = {
        "total_search_results": result.total_results,
        "strong_competitors_top10": strong,
        "beatable_listings_top10": beatable,
        "top3_review_share": round(concentration, 2),
        "avg_rating_top10": round(avg_rating, 2) if avg_rating else None,
        "sponsored_share": round(sponsored_share, 2),
        "unique_brands_top10": len(brands) if brands else None,
    }

    if concentration > 0.7 and total_reviews:
        notes.append("A few listings hold most of the reviews; the top spots are entrenched.")
    if beatable >= 3:
        notes.append(f"{beatable} of the top {len(top)} listings look beatable (few reviews or weak rating).")
    if sponsored_share >= 0.35:
        notes.append("Lots of sponsored listings: expect to pay heavily for ads.")
    if median_price is not None and median_price < 15:
        notes.append("Low median price: margins will be thin after Amazon fees.")

    # ---- Combine ----------------------------------------------------------
    demand_pts = round(demand_score * 100)
    competition_pts = round(competition * 100)
    opportunity = round(0.55 * demand_pts + 0.45 * (100 - competition_pts))

    if not top:
        verdict = "No data"
    elif opportunity >= 65:
        verdict = "Promising"
    elif opportunity >= 45:
        verdict = "Worth a closer look"
    else:
        verdict = "Tough market"

    return KeywordReport(
        keyword=result.keyword,
        source=result.source,
        demand=demand,
        supply=supply,
        demand_score=demand_pts,
        competition_score=competition_pts,
        opportunity_score=opportunity,
        verdict=verdict,
        notes=notes,
        products=result.products,
    )


def summary_row(report: KeywordReport) -> dict[str, object]:
    """Flatten a report into one row for a comparison table or CSV."""
    return {
        "keyword": report.keyword,
        "verdict": report.verdict,
        "opportunity": report.opportunity_score,
        "demand": report.demand_score,
        "competition": report.competition_score,
        **report.demand,
        **report.supply,
        "source": report.source,
    }


def product_rows(products: list[Product]) -> list[dict[str, object]]:
    return [
        {
            "asin": p.asin,
            "title": p.title,
            "brand": p.brand,
            "price": p.price,
            "rating": p.rating,
            "reviews": p.reviews,
            "monthly_sales": p.monthly_sales,
            "bsr": p.bsr,
            "sponsored": p.sponsored,
        }
        for p in products
    ]
