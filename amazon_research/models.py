"""Plain data containers shared by the providers and the analysis code."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Product:
    """One listing as it appears in the search results for a keyword."""

    asin: str
    title: str
    price: float | None = None
    rating: float | None = None
    reviews: int = 0
    brand: str | None = None
    sponsored: bool = False
    # Units sold in the last 30 days, from Amazon's "1K+ bought in past month"
    # badge or from a research tool's sales estimate. None when unknown.
    monthly_sales: int | None = None
    bsr: int | None = None


@dataclass
class SearchResult:
    """What a provider returns for a single keyword."""

    keyword: str
    products: list[Product]
    # Amazon's "1-48 of over N results" count. None when the source lacks it.
    total_results: int | None = None
    source: str = ""


@dataclass
class KeywordReport:
    keyword: str
    source: str
    demand: dict[str, float | int | None]
    supply: dict[str, float | int | None]
    demand_score: int
    competition_score: int
    opportunity_score: int
    verdict: str
    notes: list[str] = field(default_factory=list)
    products: list[Product] = field(default_factory=list)
