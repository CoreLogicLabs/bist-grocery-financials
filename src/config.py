"""Central configuration: companies, analysis window, label mappings, paths.

All deliverables are in English; Turkish strings here are the raw KAP statement
row labels returned by borsapy and exist only to be mapped to English.
"""
from __future__ import annotations
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
CACHE = ROOT / "data" / ".cache"
for _p in (DATA_RAW, DATA_PROCESSED, CACHE):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Universe — 4 BIST food-retail companies (borsapy uses plain symbols, no .IS)
# --------------------------------------------------------------------------- #
COMPANIES = {
    "BIMAS": "BİM",           # hard discount
    "MGROS": "Migros",        # full-line supermarket
    "SOKM": "Şok Marketler",  # hard discount
    "BIZIM": "Bizim Toptan",  # wholesale / cash-and-carry
}
TICKERS = list(COMPANIES.keys())
BACKUP_TICKER = "CRFSA"       # CarrefourSA — available (40q) but not needed

# yfinance equivalents (cross-check only) carry the ".IS" suffix
YF_TICKERS = {t: f"{t}.IS" for t in TICKERS}

# --------------------------------------------------------------------------- #
# Analysis window: 20 quarters, 2021Q1 .. 2025Q4
# --------------------------------------------------------------------------- #
START_YEAR, START_Q = 2021, 1
END_YEAR, END_Q = 2025, 4


def _quarter_range(y0: int, q0: int, y1: int, q1: int) -> list[str]:
    out, y, q = [], y0, q0
    while (y, q) <= (y1, q1):
        out.append(f"{y}Q{q}")
        q += 1
        if q > 4:
            q, y = 1, y + 1
    return out


QUARTERS = _quarter_range(START_YEAR, START_Q, END_YEAR, END_Q)  # len == 20
N_QUARTERS = len(QUARTERS)

# borsapy returns most-recent-first; fetch a margin of extra quarters then filter
FETCH_LAST_N = 28

# --------------------------------------------------------------------------- #
# Income-statement label map: stripped Turkish KAP row -> canonical English key.
# Source rows are CUMULATIVE (YTD); de-cumulation happens in transform.py.
# --------------------------------------------------------------------------- #
INCOME_MAP = {
    "Satış Gelirleri": "net_sales",
    "Satışların Maliyeti (-)": "cogs",
    "BRÜT KAR (ZARAR)": "gross_profit",
    "Pazarlama, Satış ve Dağıtım Giderleri (-)": "selling_dist_expense",
    "Genel Yönetim Giderleri (-)": "admin_expense",
    "Araştırma ve Geliştirme Giderleri (-)": "rnd_expense",
    "FAALİYET KARI (ZARARI)": "operating_profit",
    "SÜRDÜRÜLEN FAALİYETLER VERGİ ÖNCESİ KARI (ZARARI)": "pretax_profit",
    "DÖNEM KARI (ZARARI)": "net_profit",
    "Ana Ortaklık Payları": "net_profit_to_parent",
}

# Balance-sheet totals (snapshot, NOT cumulative). borsapy's detailed quarterly
# balance sheet is noisy (repeated "(Ara Toplam)" subtotals); only the top-level
# "TOPLAM VARLIKLAR" row is cleanly recoverable across the full window, so deep
# balance-sheet ratios are out of scope for now (income statement is the core).
BALANCE_MAP = {
    "TOPLAM VARLIKLAR": "total_assets",
}

# Cash-flow row used to build EBITDA = operating_profit + D&A (also cumulative).
# Verified against raw filings: top-level "Amortisman Giderleri" is the clean line.
CASHFLOW_DA_LABELS = [
    "Amortisman Giderleri",
    "Amortisman & İtfa Payları",
]

# Base period for real-TRY deflation: everything expressed in END-of-window prices
# so the latest quarter is unchanged and history is inflated to today's lira.
BASE_QUARTER = "2025Q4"

# --------------------------------------------------------------------------- #
# Margin / metric definitions (computed in transform.py)
# --------------------------------------------------------------------------- #
MARGIN_METRICS = {
    "gross_margin": ("gross_profit", "net_sales"),
    "operating_margin": ("operating_profit", "net_sales"),
    "net_margin": ("net_profit", "net_sales"),
    "ebitda_margin": ("ebitda", "net_sales"),
}

CURRENCY = "TRY"  # all sources are nominal Turkish lira

__all__ = [
    "ROOT", "DATA_RAW", "DATA_PROCESSED", "CACHE",
    "COMPANIES", "TICKERS", "YF_TICKERS", "BACKUP_TICKER",
    "QUARTERS", "N_QUARTERS", "FETCH_LAST_N",
    "INCOME_MAP", "BALANCE_MAP", "CASHFLOW_DA_LABELS", "BASE_QUARTER",
    "MARGIN_METRICS", "CURRENCY",
]
