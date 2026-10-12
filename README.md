# Amazon Keyword Research

Type in product keywords (like `yoga mat` or `bamboo cutting board`) and this tool tells you,
for each one:

- **Demand**: how much the top listings sell each month (units and revenue).
- **Competition**: how hard it would be to break in, based on how many reviews the leaders
  have, how many ads there are, how high the ratings are, and how many results exist.
- **Opportunity**: one 0–100 score combining the two. Higher means more demand and less
  competition.

It compares keywords side by side so you can see which product ideas are worth a closer look.

## Where the data comes from

You pick one of three sources in the app:

| Source | Cost | What it is |
|---|---|---|
| **Demo** | Free | Made-up numbers so you can try the tool. **Not real.** |
| **Rainforest API** | Paid per search | Live Amazon search results. Sign up at [rainforestapi.com](https://www.rainforestapi.com) to get an API key. Each keyword uses one request credit. |
| **Upload spreadsheet** | Free | A CSV you exported from Helium 10 (Xray), Jungle Scout or a similar tool. Use one file per keyword; the file name becomes the keyword. Try `sample_data/silicone_baking_mat.csv`. |

The tool doesn't scrape Amazon directly, because Amazon blocks scraping and forbids it in its terms.

## How to run it

You need [Python](https://www.python.org/downloads/) 3.10 or newer installed.

1. Download this project (green **Code** button on GitHub, then **Download ZIP**) and unzip it.
2. Open a terminal (Mac: *Terminal*; Windows: *Command Prompt*) in the project folder.
3. Install what it needs (one time only):
   ```
   pip install -r requirements.txt
   ```
4. Start the app:
   ```
   streamlit run app.py
   ```
   A browser tab opens with the tool. Type your keywords (one per line) and press **Analyze**.

To save your API key so you don't have to paste it every time, set the environment variable
`RAINFOREST_API_KEY` before starting the app.

### Command-line version

```
python -m amazon_research "yoga mat" "dog cooling mat"            # demo data
RAINFOREST_API_KEY=yourkey python -m amazon_research "yoga mat"   # live data
python -m amazon_research --csv sample_data/silicone_baking_mat.csv --out results.csv
```

## How the scores work

The tool looks at the top 10 **organic** (non-ad) listings for each keyword.

**Demand**
- Monthly units sold, taken from Amazon's "1K+ bought in past month" badge or from your
  spreadsheet's sales column. The badge is a minimum, so live numbers tend to be low.
- If there's no sales data, demand is estimated from review counts instead (less accurate).

**Competition**, made up of:
- Strong rivals: listings with 1,000+ reviews (35%)
- Share of the page that is sponsored ads (20%)
- Average star rating of the leaders (15%)
- How much of the reviews the top 3 listings hold (15%)
- Total number of search results (15%)

**Beatable listings** are top-10 listings with fewer than 200 reviews or a rating under 4.0,
which are spots a new seller could realistically take.

**Opportunity** = 55% demand + 45% (100 − competition).
- 65 or higher: *Promising*
- 45 to 64: *Worth a closer look*
- Below 45: *Tough market*

These are rules of thumb for **comparing** keywords, not guarantees. Always look at the real
Amazon search page and work out your margins (product cost, shipping, FBA fees, ads) before
ordering inventory.

## For developers

```
pytest
```

The code lives in `amazon_research/`. `analysis.py` holds the scoring, and `providers/` holds
the data sources. To add a new source, write a class with a `search(keyword) -> SearchResult`
method.
