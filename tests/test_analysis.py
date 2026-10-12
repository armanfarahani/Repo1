import io

import pytest

from amazon_research import Product, SearchResult, analyze
from amazon_research.providers import DemoProvider, load_csv
from amazon_research.providers.rainforest import _to_product, parse_bought_badge


def make(reviews, sales=None, rating=4.5, sponsored=False, price=25.0):
    return Product(asin="X", title="t", price=price, rating=rating, reviews=reviews,
                   sponsored=sponsored, monthly_sales=sales, brand="b")


def test_easy_market_beats_crowded_market():
    easy = SearchResult("easy", [make(80, sales=2000, rating=3.8) for _ in range(10)], total_results=800)
    crowded = SearchResult(
        "crowded",
        [make(30000, sales=2000, rating=4.8) for _ in range(10)] + [make(5000, sponsored=True)] * 8,
        total_results=200_000,
    )
    e, c = analyze(easy), analyze(crowded)
    assert e.competition_score < c.competition_score
    assert e.opportunity_score > c.opportunity_score
    assert e.supply["beatable_listings_top10"] == 10
    assert c.supply["strong_competitors_top10"] == 10


def test_sponsored_listings_excluded_from_top10():
    products = [make(100000, sponsored=True)] + [make(10, sales=50) for _ in range(10)]
    report = analyze(SearchResult("k", products))
    assert report.supply["strong_competitors_top10"] == 0
    assert report.demand["est_monthly_units_top10"] == 500


def test_falls_back_to_reviews_without_sales():
    report = analyze(SearchResult("k", [make(5000) for _ in range(10)]))
    assert report.demand["est_monthly_units_top10"] is None
    assert report.demand_score > 0
    assert any("review counts only" in n for n in report.notes)


def test_empty_results():
    report = analyze(SearchResult("k", []))
    assert report.verdict == "No data"


@pytest.mark.parametrize("text,expected", [
    ("1K+ bought in past month", 1000),
    ("2.5K+ bought in past month", 2500),
    ("50+ bought in past month", 50),
    ("", None),
    ("Limited time deal", None),
])
def test_parse_bought_badge(text, expected):
    assert parse_bought_badge(text) == expected


def test_rainforest_item_parsing():
    p = _to_product({
        "asin": "B0", "title": "Mat", "price": {"value": 19.99}, "rating": 4.4,
        "ratings_total": 321, "sponsored": True, "recent_sales": "3K+ bought in past month",
    })
    assert (p.price, p.reviews, p.sponsored, p.monthly_sales) == (19.99, 321, True, 3000)


def test_demo_is_deterministic():
    a, b = DemoProvider().search("yoga mat"), DemoProvider().search("Yoga Mat")
    assert [p.reviews for p in a.products] == [p.reviews for p in b.products]


def test_csv_import_loose_headers():
    csv = io.StringIO(
        "ASIN,Product Title,Price ($),Ratings,Review Count,Brand,ASIN Sales,BSR\n"
        "B01,Mat,\"$1,029.50\",4.6,\"1,204\",Acme,900,1500\n"
        "B02,Mat 2,$19.00,4.1,15,,120,\n"
    )
    result = load_csv(csv, keyword="mats")
    first, second = result.products
    assert first.price == 1029.50 and first.reviews == 1204 and first.monthly_sales == 900
    assert first.rating == 4.6 and first.bsr == 1500
    assert second.brand is None and second.bsr is None


def test_csv_import_requires_demand_column():
    with pytest.raises(ValueError):
        load_csv(io.StringIO("ASIN,Title\nB01,x\n"), keyword="k")
