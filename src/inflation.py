"""Turkish CPI (TÜFE) helper — turns borsapy's monthly inflation rates into a
quarterly price index and per-quarter deflators for real-TRY analysis.

borsapy's ``Inflation().tufe()`` returns monthly YoY/MoM inflation *rates*, not an
index level. We chain the month-over-month rates into a relative index; only
ratios between quarters matter for deflation, so the arbitrary starting level is
irrelevant. Cross-checked against ``Inflation().calculate(amount, start, end)``.
"""
from __future__ import annotations
import pandas as pd

from .ssl_setup import configure_ssl
from . import config as C

_CPI_CACHE = C.DATA_RAW / "cpi_tufe.csv"
_QEND_MONTH = {1: 3, 2: 6, 3: 9, 4: 12}  # quarter -> quarter-end month


def fetch_tufe(start: str = "2019-01-01", end: str = "2026-03-31",
               refresh: bool = False) -> pd.DataFrame:
    """Fetch (and cache) monthly TÜFE inflation rates as a tidy ascending frame."""
    if _CPI_CACHE.exists() and not refresh:
        df = pd.read_csv(_CPI_CACHE, parse_dates=["Date"])
    else:
        configure_ssl()
        import borsapy as bp
        raw = bp.Inflation().tufe(start=start, end=end)
        df = raw.reset_index().rename(columns={"index": "Date"})
        df.to_csv(_CPI_CACHE, index=False, encoding="utf-8")
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def monthly_cpi_index(refresh: bool = False) -> pd.Series:
    """Relative CPI index (monthly), chained from month-over-month rates."""
    df = fetch_tufe(refresh=refresh)
    factor = 1.0 + df["MonthlyInflation"].astype(float) / 100.0
    idx = factor.cumprod()
    idx.index = pd.to_datetime(df["Date"]).dt.to_period("M")
    return idx


def quarterly_cpi_index(refresh: bool = False) -> pd.Series:
    """CPI index sampled at each quarter-end month, keyed by 'YYYYQq'."""
    m = monthly_cpi_index(refresh=refresh)
    out: dict[str, float] = {}
    for period, val in m.items():
        if period.month in _QEND_MONTH.values():
            q = (period.month) // 3
            out[f"{period.year}Q{q}"] = float(val)
    return pd.Series(out, name="cpi_index")


def quarterly_deflators(base_quarter: str = C.BASE_QUARTER,
                        refresh: bool = False) -> pd.Series:
    """deflator[q] = CPI[base] / CPI[q]; multiply nominal TRY by it to get
    base-quarter (real) TRY. Latest/base quarter deflator == 1.0."""
    cpi = quarterly_cpi_index(refresh=refresh)
    if base_quarter not in cpi.index:
        raise KeyError(f"base quarter {base_quarter} not in CPI index "
                       f"({cpi.index.min()}..{cpi.index.max()})")
    return (cpi.loc[base_quarter] / cpi).rename("deflator")


if __name__ == "__main__":
    d = quarterly_deflators()
    cpi = quarterly_cpi_index()
    show = pd.DataFrame({"cpi_index": cpi, "deflator": d}).loc[C.QUARTERS]
    print(show.round(4).to_string())
