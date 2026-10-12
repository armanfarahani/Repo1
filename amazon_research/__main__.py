"""Command-line version: python -m amazon_research "yoga mat" "dog bed" """

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

from .analysis import analyze, summary_row
from .providers import DemoProvider, RainforestProvider, load_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare demand and competition for Amazon keywords.")
    parser.add_argument("keywords", nargs="*", help="Keywords to research")
    parser.add_argument(
        "--source",
        choices=["demo", "rainforest"],
        default="rainforest" if os.environ.get("RAINFOREST_API_KEY") else "demo",
        help="Where to get data (default: rainforest if RAINFOREST_API_KEY is set, else demo)",
    )
    parser.add_argument("--csv", action="append", default=[], metavar="FILE",
                        help="Analyze a Helium 10 / Jungle Scout export (repeatable)")
    parser.add_argument("--domain", default="amazon.com", help="Amazon marketplace, e.g. amazon.co.uk")
    parser.add_argument("--out", help="Save the comparison table to this CSV file")
    args = parser.parse_args(argv)

    if not args.keywords and not args.csv:
        parser.error("give at least one keyword or --csv file")

    results = [load_csv(path, keyword=os.path.splitext(os.path.basename(path))[0].replace("_", " ")) for path in args.csv]
    if args.keywords:
        if args.source == "rainforest":
            provider = RainforestProvider(os.environ.get("RAINFOREST_API_KEY", ""), args.domain)
        else:
            provider = DemoProvider()
            print("Using DEMO data (made up). Set RAINFOREST_API_KEY for real data.\n", file=sys.stderr)
        results += [provider.search(k) for k in args.keywords]

    reports = sorted((analyze(r) for r in results), key=lambda r: r.opportunity_score, reverse=True)

    table = pd.DataFrame([summary_row(r) for r in reports])
    cols = ["keyword", "verdict", "opportunity", "demand", "competition",
            "est_monthly_units_top10", "median_price", "strong_competitors_top10",
            "beatable_listings_top10"]
    print(table[cols].to_string(index=False))
    for r in reports:
        if r.notes:
            print(f"\n{r.keyword}:")
            for note in r.notes:
                print(f"  - {note}")

    if args.out:
        table.to_csv(args.out, index=False)
        print(f"\nSaved full table to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
