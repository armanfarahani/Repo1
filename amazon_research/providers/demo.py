"""Made-up but realistic-looking data, so the tool can be tried without an API key.

The same keyword always produces the same numbers. None of it reflects
real Amazon listings.
"""

from __future__ import annotations

import hashlib
import random

from ..models import Product, SearchResult


class DemoProvider:
    name = "demo (fake data)"

    def search(self, keyword: str) -> SearchResult:
        seed = int(hashlib.sha256(keyword.lower().encode()).hexdigest(), 16) % 2**32
        rng = random.Random(seed)

        # Each keyword gets its own market "personality".
        popularity = rng.uniform(0.3, 3.0)  # scales sales
        maturity = rng.uniform(0.2, 1.0)  # how entrenched the leaders are
        base_price = rng.choice([9.99, 14.99, 19.99, 24.99, 34.99, 49.99, 79.99])
        brands = [f"Brand{chr(65 + i)}" for i in range(rng.randint(5, 14))]

        products: list[Product] = []
        for rank in range(48):
            sponsored = rng.random() < 0.15 + 0.25 * maturity
            decay = 1 / (1 + rank * 0.35)
            reviews = int(rng.lognormvariate(7.5 * maturity + 2, 1.0) * decay)
            sales = int(rng.lognormvariate(6.5, 0.8) * popularity * decay)
            products.append(
                Product(
                    asin=f"DEMO{seed % 100000:05d}{rank:02d}",
                    title=f"{keyword.title()} - demo listing #{rank + 1}",
                    price=round(base_price * rng.uniform(0.7, 1.5), 2),
                    rating=round(min(5.0, rng.gauss(4.1 + 0.5 * maturity, 0.25)), 1),
                    reviews=reviews,
                    brand=rng.choice(brands),
                    sponsored=sponsored,
                    monthly_sales=sales,
                )
            )

        return SearchResult(
            keyword=keyword,
            products=products,
            total_results=int(rng.lognormvariate(9, 1.2)),
            source=self.name,
        )
