"""Web app. Start it with:  streamlit run app.py"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from amazon_research import analyze, product_rows, summary_row
from amazon_research.providers import DemoProvider, RainforestProvider, load_csv

st.set_page_config(page_title="Amazon Keyword Research", page_icon="📦", layout="wide")
st.title("📦 Amazon Keyword Research")
st.caption("Type keywords to compare how much demand each one has against how crowded it is.")

# ---- Sidebar: where the data comes from ------------------------------------
with st.sidebar:
    st.header("Data source")
    source = st.radio(
        "Get product data from",
        ["Demo (fake data, free)", "Rainforest API (live Amazon data)", "Upload spreadsheet"],
        help="Start with Demo to see how it works. Switch to live data once you have an API key.",
    )
    api_key = domain = None
    if source.startswith("Rainforest"):
        api_key = st.text_input(
            "Rainforest API key", value=os.environ.get("RAINFOREST_API_KEY", ""), type="password"
        )
        domain = st.selectbox(
            "Marketplace",
            ["amazon.com", "amazon.ca", "amazon.co.uk", "amazon.de", "amazon.com.au", "amazon.in"],
        )
        st.caption("Each keyword uses 1 request credit. Get a key at rainforestapi.com.")

    st.divider()
    st.markdown(
        "**How to read the scores**\n\n"
        "- **Demand** – how much page-one listings sell.\n"
        "- **Competition** – how hard it is to break in (big review counts, lots of ads, "
        "high ratings).\n"
        "- **Opportunity** – high demand plus low competition. Higher is better."
    )

# ---- Input -----------------------------------------------------------------
results = []
if source.startswith("Upload"):
    st.write(
        "Upload one CSV per keyword (for example a Helium 10 Xray or Jungle Scout export of a "
        "search results page). The file name is used as the keyword."
    )
    files = st.file_uploader("Spreadsheet exports", type="csv", accept_multiple_files=True)
    if files and st.button("Analyze", type="primary"):
        for f in files:
            try:
                results.append(load_csv(f, keyword=os.path.splitext(f.name)[0].replace("_", " ")))
            except Exception as e:  # show the problem but keep going with other files
                st.error(f"{f.name}: {e}")
else:
    text = st.text_area(
        "Keywords (one per line)",
        placeholder="yoga mat\nbamboo cutting board\ndog cooling mat",
        height=130,
    )
    keywords = [k.strip() for k in text.splitlines() if k.strip()]
    if st.button("Analyze", type="primary", disabled=not keywords):
        if source.startswith("Rainforest"):
            if not api_key:
                st.error("Enter your Rainforest API key in the sidebar first.")
                st.stop()
            provider = RainforestProvider(api_key, domain)
        else:
            provider = DemoProvider()
        progress = st.progress(0.0)
        for i, keyword in enumerate(keywords):
            try:
                results.append(provider.search(keyword))
            except Exception as e:
                st.error(f"“{keyword}”: {e}")
            progress.progress((i + 1) / len(keywords), text=f"Searched “{keyword}”")
        progress.empty()

if results:
    st.session_state["reports"] = sorted(
        (analyze(r) for r in results), key=lambda r: r.opportunity_score, reverse=True
    )

reports = st.session_state.get("reports")
if not reports:
    st.info("Enter some keywords and press **Analyze**.")
    st.stop()

if any(r.source.startswith("demo") for r in reports):
    st.warning("These results use **made-up demo data**. Switch the data source to get real numbers.")

# ---- Comparison ------------------------------------------------------------
st.subheader("Comparison")
table = pd.DataFrame([summary_row(r) for r in reports])
st.dataframe(
    table[["keyword", "verdict", "opportunity", "demand", "competition",
           "est_monthly_units_top10", "est_monthly_revenue_top10", "median_price",
           "strong_competitors_top10", "beatable_listings_top10", "sponsored_share"]],
    hide_index=True,
    width="stretch",
    column_config={
        "keyword": "Keyword",
        "verdict": "Verdict",
        "opportunity": st.column_config.ProgressColumn("Opportunity", min_value=0, max_value=100, format="%d"),
        "demand": st.column_config.ProgressColumn("Demand", min_value=0, max_value=100, format="%d"),
        "competition": st.column_config.ProgressColumn("Competition", min_value=0, max_value=100, format="%d"),
        "est_monthly_units_top10": st.column_config.NumberColumn("Units/mo (top 10)", format="%d"),
        "est_monthly_revenue_top10": st.column_config.NumberColumn("Revenue/mo (top 10)", format="$%d"),
        "median_price": st.column_config.NumberColumn("Median price", format="$%.2f"),
        "strong_competitors_top10": "Strong rivals (1k+ reviews)",
        "beatable_listings_top10": "Beatable listings",
        "sponsored_share": st.column_config.NumberColumn("Ad share", format="percent"),
    },
)
st.download_button(
    "Download table as CSV",
    table.to_csv(index=False).encode(),
    file_name="keyword_research.csv",
    mime="text/csv",
)

if len(reports) > 1:
    st.scatter_chart(
        table, x="competition", y="demand", color="keyword", size=200,
        x_label="Competition (lower is easier)", y_label="Demand (higher is better)",
    )
    st.caption("Best spot is top-left: lots of demand, little competition.")

# ---- Per-keyword detail ----------------------------------------------------
st.subheader("Details")
for r in reports:
    with st.expander(f"{r.keyword} — {r.verdict} (opportunity {r.opportunity_score})"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Demand", r.demand_score)
        c2.metric("Competition", r.competition_score)
        c3.metric("Opportunity", r.opportunity_score)
        for note in r.notes:
            st.write(f"• {note}")
        st.dataframe(pd.DataFrame(product_rows(r.products)), hide_index=True, width="stretch")

st.caption(
    "Scores are rules of thumb for comparing keywords, not guarantees. "
    "Always check the actual Amazon search page before ordering inventory."
)
