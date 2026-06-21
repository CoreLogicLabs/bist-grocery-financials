"""Fetch raw quarterly statements from borsapy (primary source).

borsapy serves official KAP filings for BIST companies. Income-statement values
are CUMULATIVE (year-to-date); de-cumulation is handled in transform.py, not here
-- this module only pulls and persists the raw statements verbatim.

Run from the project root:
    python -m src.fetch
"""
from __future__ import annotations
import sys
import time

import pandas as pd

from .ssl_setup import configure_ssl
from . import config as C

configure_ssl()
import borsapy as bp  # noqa: E402  (import after SSL is configured)


def _get(ticker_obj, getter: str, prop: str, last_n: int) -> pd.DataFrame | None:
    """Call get_*(quarterly=True, last_n=...) if available, else fall back to the property."""
    fn = getattr(ticker_obj, getter, None)
    if callable(fn):
        try:
            return fn(quarterly=True, last_n=last_n)
        except TypeError:
            try:
                return fn(quarterly=True)
            except Exception:
                pass
        except Exception:
            pass
    return getattr(ticker_obj, prop, None)


def fetch_company(ticker: str, last_n: int = C.FETCH_LAST_N) -> dict[str, pd.DataFrame]:
    """Pull income / balance / cashflow for one ticker and persist to data/raw."""
    t = bp.Ticker(ticker)
    out: dict[str, pd.DataFrame] = {}
    specs = [
        ("income", "get_income_stmt", "quarterly_income_stmt"),
        ("balance", "get_balance_sheet", "quarterly_balance_sheet"),
        ("cashflow", "get_cashflow", "quarterly_cashflow"),
    ]
    for kind, getter, prop in specs:
        df = _get(t, getter, prop, last_n)
        if df is None or getattr(df, "empty", True):
            print(f"  ! {ticker} {kind}: empty / unavailable")
            continue
        df.to_csv(C.DATA_RAW / f"{ticker}_{kind}.csv", encoding="utf-8")
        out[kind] = df
        print(f"  - {ticker} {kind}: {df.shape[0]} rows x {df.shape[1]} quarters "
              f"[{list(df.columns)[-1]}..{list(df.columns)[0]}]")
    return out


def fetch_all(tickers: list[str] | None = None) -> dict[str, dict[str, pd.DataFrame]]:
    tickers = tickers or C.TICKERS
    print(f"Fetching {len(tickers)} companies from borsapy "
          f"(target window {C.QUARTERS[0]}..{C.QUARTERS[-1]}, {C.N_QUARTERS} quarters)\n")
    results: dict[str, dict[str, pd.DataFrame]] = {}
    for tk in tickers:
        print(f"{tk} ({C.COMPANIES.get(tk, '?')})")
        results[tk] = fetch_company(tk)
        time.sleep(0.5)  # be polite to the source
    print(f"\nRaw CSVs written to {C.DATA_RAW}")
    return results


if __name__ == "__main__":
    fetch_all(sys.argv[1:] or None)
