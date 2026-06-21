"""Streamlit dashboard — BIST food-retail quarterly financials.

Run from the project root:
    streamlit run dashboard/app.py
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

MARGINS = {
    "Gross margin": "gross_margin",
    "Operating margin": "operating_margin",
    "Net margin": "net_margin",
    "EBITDA margin": "ebitda_margin",
}

st.set_page_config(page_title="BIST Food Retail — Quarterly Financials", layout="wide")


@st.cache_data
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    q = pd.read_csv(PROCESSED / "quarterly_panel.csv")
    a = pd.read_csv(PROCESSED / "annual_panel.csv")
    return q, a


def main() -> None:
    st.title("🛒 BIST Food Retail — Quarterly Financial Performance")
    st.caption("BİM · Migros · Şok · Bizim Toptan  |  2021Q1–2025Q4  |  "
               "Source: borsapy (KAP filings), cross-checked vs Yahoo Finance")

    if not (PROCESSED / "quarterly_panel.csv").exists():
        st.error("Processed data not found. Run `python -m src.fetch` then "
                 "`python -m src.transform` first.")
        st.stop()

    q, a = load()
    names = q.drop_duplicates("company")[["company", "company_name"]]
    label_of = dict(zip(names["company"], names["company_name"]))

    with st.sidebar:
        st.header("Filters")
        companies = st.multiselect(
            "Companies", options=list(label_of), default=list(label_of),
            format_func=lambda c: f"{label_of[c]} ({c})")
        metric_label = st.selectbox("Margin metric", list(MARGINS))
        metric = MARGINS[metric_label]

    with st.expander("⚠️ Methodology note — Turkish inflation accounting (TMS 29)"):
        st.markdown(
            "From FY2023, BIST companies report under inflation accounting (TMS 29). "
            "Single-quarter figures from differencing year-to-date statements are "
            "**unreliable**, so the analysis uses **margins on cumulative YTD figures** "
            "(inflation-neutral) and **annual figures** for level comparison. "
            "Operating margins reflect inflation restatement of COGS/depreciation, while "
            "net margins are lifted by monetary-position gains. Real-TRY (CPI-deflated) "
            "figures are **indicative**: 2021–2022 sit partly on historical cost vs the "
            "restated 2023+ base.")

    qf = q[q["company"].isin(companies)]

    tab1, tab2, tab3 = st.tabs(["📈 Margin trends", "🏁 Comparison", "💵 Real-TRY (annual)"])

    with tab1:
        st.subheader(f"{metric_label} over time (cumulative YTD basis)")
        wide = qf.pivot(index="quarter", columns="company", values=metric)
        wide.columns = [label_of[c] for c in wide.columns]
        st.line_chart(wide, height=420)
        st.caption("Margins computed as ratio of cumulative YTD profit to cumulative YTD net sales.")

    with tab2:
        latest_q = q["quarter"].max()
        st.subheader(f"Margin comparison — latest quarter ({latest_q}, YTD)")
        latest = qf[qf["quarter"] == latest_q]
        comp = latest.set_index("company")[list(MARGINS.values())]
        comp.index = [label_of[c] for c in comp.index]
        comp.columns = list(MARGINS)
        st.bar_chart(comp, height=420)
        st.dataframe(comp.style.format("{:.1f}%"), use_container_width=True)

    with tab3:
        st.subheader("Annual net sales in real TRY (base = 2025Q4 prices)")
        st.caption("Indicative — see methodology note on the 2021–2022 vs 2023+ basis break.")
        af = a[a["company"].isin(companies)].copy()
        af["net_sales_fy_real_B"] = af["net_sales_fy_real"] / 1e9
        wide = af.pivot(index="year", columns="company", values="net_sales_fy_real_B")
        wide.columns = [label_of[c] for c in wide.columns]
        st.bar_chart(wide, height=420)
        st.dataframe(wide.style.format("{:,.1f} B₺"), use_container_width=True)


if __name__ == "__main__":
    main()
