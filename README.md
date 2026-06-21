# BIST Food Retail — Quarterly Financial Performance (2021–2025)

Exploratory financial analysis of the four publicly listed Turkish food-retailers,
across 20 quarters (2021Q1–2025Q4):

| Ticker | Company | Business model |
|--------|---------|----------------|
| `BIMAS` | BİM | Hard discount |
| `MGROS` | Migros | Full-line supermarket |
| `SOKM` | Şok Marketler | Hard discount |
| `BIZIM` | Bizim Toptan | Wholesale / cash-and-carry |

The headline result is that **profitability margins track business models cleanly** —
the full-line supermarket (Migros) earns the highest gross margin (~24%), the hard
discounters sit in the middle (BİM ~19%, Şok ~20%), and the wholesaler (Bizim) the
lowest (~17%) — and that all four show a visible **margin compression in 2022–2023**
that coincides with the adoption of inflation accounting, followed by a recovery.

## 📓 Read the analysis

The full exploratory analysis, with all charts rendered inline, is in
**[`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb)** — it renders directly on GitHub,
so you can read it end-to-end with no setup.

## Live dashboard

_Coming soon — deploying to Streamlit Community Cloud._
(Run locally meanwhile: `streamlit run dashboard/app.py`.)

## Why this is not a trivial dataset

Turkey has run very high inflation over the window (cumulative CPI ≈ **6.7×** from
2021Q1 to 2025Q4), and from FY2023 listed companies report under **inflation
accounting (TMS 29 / IAS 29)**. This breaks naïve analysis in two ways the project
handles explicitly:

1. **Discrete quarters are unreliable.** Annual (Q4) figures are restated to
   year-end prices while interim quarters sit on different price bases, so
   differencing year-to-date statements produces artifacts (e.g. a single-quarter
   revenue that exceeds the full year). → The analysis is built on **margins over
   cumulative YTD figures** (inflation-neutral ratios) and on **annual figures**.
2. **Nominal TRY growth is mostly inflation.** → Levels are compared in **real TRY**
   (CPI-deflated to 2025Q4 prices) as an *indicative, clearly-caveated* secondary
   view, and growth is shown as YTD-over-YTD.

A documented side-effect of TMS 29 visible in the data: **operating margins turn
negative while net margins stay positive**, because monetary-position gains (retailers
carry large net trade payables) are recognised below the operating line.

## Data sources

| | Primary | Secondary |
|--|---------|-----------|
| Library | **borsapy** (Apache-2.0) | yfinance (Apache-2.0) |
| Underlying data | KAP official filings | Yahoo Finance |
| Depth (quarterly) | ~38–40 quarters (back to 2016) | only ~5–6 quarters |
| Currency | TRY | TRY |
| Role | full history, all statements | cross-check / English labels |

borsapy is primary because Yahoo only retains ~5 quarters of fundamentals for BIST
tickers — far short of a 5-year quarterly study. borsapy returns the full statements
straight from KAP (in Turkish; mapped to English in [`src/config.py`](src/config.py)).

## Project structure

```
bist-grocery-financials/
├── src/
│   ├── config.py       # companies, window, TR→EN label maps, paths
│   ├── ssl_setup.py    # combined CA bundle (certifi + OS trust store) for curl_cffi
│   ├── inflation.py    # TÜFE CPI → quarterly price index & deflators
│   ├── fetch.py        # pull raw statements from borsapy  →  data/raw/
│   └── transform.py    # YTD margins, robust TTM, annual real-TRY  →  data/processed/
├── notebooks/01_eda.ipynb     # exploratory analysis + charts
├── dashboard/app.py           # Streamlit dashboard
├── data/{raw,processed}/      # generated locally (git-ignored); regenerate with the steps below
├── requirements.txt
└── README.md
```

> **Note on data.** The `data/` directory is **not committed** — raw KAP statements and
> the derived panels are regenerated locally via the two commands below. This keeps the
> repository free of bulk source data; the notebook already embeds its charts, so it
> renders on GitHub without any data files present.

## Setup & run

```bash
pip install -r requirements.txt

# 1) pull raw statements from borsapy            -> data/raw/*.csv
python -m src.fetch
# 2) build analysis panels                       -> data/processed/*.csv
python -m src.transform
# 3a) explore
jupyter lab notebooks/01_eda.ipynb
# 3b) or launch the dashboard
streamlit run dashboard/app.py
```

> **SSL note.** On machines with a TLS-intercepting antivirus/proxy (e.g. Norton),
> `yfinance`/`curl_cffi` fails certificate verification because it ignores Python's
> trust store. `src/ssl_setup.py` builds a combined CA bundle (certifi + OS roots)
> and points `CURL_CA_BUNDLE` at it. Verification is **never disabled**.

## Outputs

These files are produced locally by `python -m src.transform` (not committed):

- `data/processed/quarterly_panel.csv` — per company × quarter: YTD levels, **margins**,
  YTD-over-YTD growth, **real-TRY TTM** net sales, total assets.
- `data/processed/annual_panel.csv` — per company × year: FY levels (nominal & real),
  FY margins, nominal/real YoY.
- `data/processed/quarterly_discrete_reference.csv` — discrete quarters, **reference
  only** (unreliable under TMS 29; kept for transparency).

## Limitations

- **Real-TRY levels are indicative**, not exact: 2021–2022 partly sit on historical
  cost vs the restated 2023+ base; cross-era real comparison should be read with care.
- **Balance-sheet depth is out of scope.** borsapy's detailed quarterly balance sheet
  returns noisy, duplicated subtotal rows; only `total_assets` is cleanly recovered.
- Figures are as-reported consolidated statements; no manual restatement is applied.

## License & attribution

Code: MIT. This is an **educational / portfolio** project, not investment advice. Data is
sourced from public KAP disclosures via borsapy and from Yahoo Finance via yfinance for
personal/educational use — please attribute both sources and **do not redistribute the
underlying data commercially**.
