"""Load a keyword's search results from a spreadsheet export.

Works with exports from Helium 10 (Xray), Jungle Scout, or any CSV that
has columns for things like ASIN, price, rating, reviews and sales.
Column names are matched loosely, so exact headers don't matter.
"""

from __future__ import annotations

import re
from typing import IO

import pandas as pd

from ..models import Product, SearchResult

# For each field, header names to look for (lowercased, letters/digits only).
COLUMN_ALIASES: dict[str, list[str]] = {
    "asin": ["asin"],
    "title": ["title", "producttitle", "productname", "product", "name"],
    "price": ["price", "price$", "priceusd"],
    "rating": ["rating", "ratings", "stars", "averagerating"],
    "reviews": ["reviews", "reviewcount", "ratingscount", "ratingcount", "numberofreviews", "ratingstotal"],
    "brand": ["brand"],
    "monthly_sales": ["asinsales", "monthlysales", "sales", "estmonthlysales", "estimatedmonthlysales", "unitssold"],
    "bsr": ["bsr", "bestsellersrank", "rank", "salesrank"],
    "sponsored": ["sponsored", "issponsored", "ad"],
}


def _normalize(header: str) -> str:
    return re.sub(r"[^a-z0-9$]", "", header.lower())


def _to_number(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = re.sub(r"[^0-9.\-]", "", str(value))
    try:
        return float(text) if text else None
    except ValueError:
        return None


def _to_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "yes", "y", "1", "sponsored"}


def load_csv(file: str | IO, keyword: str, total_results: int | None = None) -> SearchResult:
    df = pd.read_csv(file)
    by_norm = {_normalize(c): c for c in df.columns}
    columns = {
        field: next((by_norm[a] for a in aliases if a in by_norm), None)
        for field, aliases in COLUMN_ALIASES.items()
    }
    if not columns["asin"] and not columns["title"]:
        raise ValueError("The file needs at least an 'ASIN' or 'Title' column.")
    if not columns["reviews"] and not columns["monthly_sales"]:
        raise ValueError("The file needs a 'Reviews' or 'Sales' column to measure demand.")

    def get(row: pd.Series, field: str) -> object:
        col = columns[field]
        return row[col] if col else None

    products = []
    for i, row in df.iterrows():
        sales = _to_number(get(row, "monthly_sales"))
        bsr = _to_number(get(row, "bsr"))
        brand = get(row, "brand")
        products.append(
            Product(
                asin=str(get(row, "asin") or f"row{i + 1}"),
                title=str(get(row, "title") or ""),
                price=_to_number(get(row, "price")),
                rating=_to_number(get(row, "rating")),
                reviews=int(_to_number(get(row, "reviews")) or 0),
                brand=str(brand) if brand is not None and not pd.isna(brand) else None,
                sponsored=_to_bool(get(row, "sponsored")) if columns["sponsored"] else False,
                monthly_sales=int(sales) if sales is not None else None,
                bsr=int(bsr) if bsr is not None else None,
            )
        )

    return SearchResult(
        keyword=keyword,
        products=products,
        total_results=total_results,
        source="spreadsheet import",
    )
