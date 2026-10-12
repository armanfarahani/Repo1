"""Live Amazon search results via Rainforest API (https://www.rainforestapi.com).

Rainforest is a paid service that fetches Amazon pages for you, so you do
not have to scrape Amazon yourself (which Amazon blocks and forbids).
Each keyword costs one request credit.
"""

from __future__ import annotations

import re

import requests

from ..models import Product, SearchResult

API_URL = "https://api.rainforestapi.com/request"


def parse_bought_badge(text: str | None) -> int | None:
    """Turn Amazon's '2K+ bought in past month' badge into a number (2000).

    The badge is a lower bound, so the result understates true sales.
    """
    if not text:
        return None
    match = re.search(r"([\d.,]+)\s*([KkMm]?)\+?\s*bought", text)
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    suffix = match.group(2).lower()
    if suffix == "k":
        number *= 1_000
    elif suffix == "m":
        number *= 1_000_000
    return int(number)


def _to_product(item: dict) -> Product:
    price = item.get("price") or (item.get("prices") or [{}])[0]
    bsr_list = item.get("bestsellers_rank") or []
    return Product(
        asin=item.get("asin", ""),
        title=item.get("title", ""),
        price=price.get("value") if isinstance(price, dict) else None,
        rating=item.get("rating"),
        reviews=int(item.get("ratings_total") or 0),
        brand=item.get("brand"),
        sponsored=bool(item.get("sponsored")),
        monthly_sales=parse_bought_badge(item.get("recent_sales")),
        bsr=bsr_list[0].get("rank") if bsr_list else None,
    )


class RainforestProvider:
    name = "Rainforest API (live)"

    def __init__(self, api_key: str, amazon_domain: str = "amazon.com", timeout: int = 60):
        if not api_key:
            raise ValueError("A Rainforest API key is required.")
        self.api_key = api_key
        self.amazon_domain = amazon_domain
        self.timeout = timeout

    def search(self, keyword: str) -> SearchResult:
        response = requests.get(
            API_URL,
            params={
                "api_key": self.api_key,
                "type": "search",
                "amazon_domain": self.amazon_domain,
                "search_term": keyword,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        info = data.get("request_info") or {}
        if info.get("success") is False:
            raise RuntimeError(info.get("message") or "Rainforest API request failed.")

        products = [_to_product(item) for item in data.get("search_results") or []]
        total = (data.get("search_information") or {}).get("total_results")
        return SearchResult(
            keyword=keyword,
            products=products,
            total_results=int(total) if total else None,
            source=self.name,
        )
