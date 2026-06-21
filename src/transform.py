"""Build analysis-ready panels from raw borsapy statements.

Methodology note — Turkish inflation accounting (TMS 29, from FY2023):
    Single-quarter (discrete) figures obtained by differencing YTD statements are
    UNRELIABLE, because annual (Q4) figures are restated to year-end prices while
    interim quarters sit on different price bases. We therefore build the core
    analysis on robust constructs only:
      * margins on CUMULATIVE YTD figures (inflation-neutral ratios);
      * TTM (trailing-twelve-month) levels assembled purely from cumulative
        figures: TTM_q = YTD_q + FY_{y-1} - YTD_{q, y-1}  (no discrete differencing);
      * annual (FY = Q4 YTD) figures for nominal vs real-TRY level comparison.
    Discrete quarters are still emitted to a clearly-labelled *reference* file.

Run from the project root:
    python -m src.transform
"""
from __future__ import annotations
import pandas as pd

from . import config as C
from .inflation import quarterly_deflators, quarterly_cpi_index

_LEVELS = ["net_sales", "gross_profit", "operating_profit", "net_profit", "ebitda"]


# --------------------------------------------------------------------------- #
# Loading / row selection
# --------------------------------------------------------------------------- #
def _load_statement(ticker: str, kind: str) -> pd.DataFrame:
    df = pd.read_csv(C.DATA_RAW / f"{ticker}_{kind}.csv", index_col=0)
    df.index = df.index.map(lambda s: str(s).strip())  # drop KAP indentation
    return df.sort_index(axis=1)  # quarters ascending (oldest -> newest)


def _pick_rows(df: pd.DataFrame, label_map: dict[str, str]) -> pd.DataFrame:
    rows = {}
    for tr_label, canon in label_map.items():
        if tr_label in df.index:
            row = df.loc[tr_label]
            rows[canon] = row.iloc[0] if isinstance(row, pd.DataFrame) else row
    return pd.DataFrame(rows)  # index=quarter, columns=metric


def _first_label(df: pd.DataFrame, candidates: list[str]) -> pd.Series | None:
    for lab in candidates:
        if lab in df.index:
            row = df.loc[lab]
            return row.iloc[0] if isinstance(row, pd.DataFrame) else row
    return None


def decumulate(cum: pd.DataFrame) -> pd.DataFrame:
    """YTD -> discrete (reference only). Assumes a gap-free ascending index."""
    qn = cum.index.to_series().str[-1].astype(int)
    disc = cum - cum.shift(1)
    disc.loc[qn == 1] = cum.loc[qn == 1]
    return disc


# --------------------------------------------------------------------------- #
# Core builders
# --------------------------------------------------------------------------- #
def _cumulative_frame(ticker: str) -> pd.DataFrame:
    """Cumulative-YTD income metrics + YTD D&A + EBITDA, full fetched range."""
    inc = _load_statement(ticker, "income")
    cf = _load_statement(ticker, "cashflow")
    cum = _pick_rows(inc, C.INCOME_MAP).astype(float)
    da = _first_label(cf, C.CASHFLOW_DA_LABELS)
    if da is not None:
        cum["da"] = da.astype(float)
        cum["ebitda"] = cum["operating_profit"] + cum["da"]
    return cum.sort_index()


def _ttm(ytd: pd.Series) -> pd.Series:
    """Trailing-twelve-month from cumulative figures only (no differencing)."""
    idx = ytd.index
    year = idx.str.slice(0, 4).astype(int)
    q = idx.str.slice(5, 6).astype(int)
    fy_by_year = {int(y): ytd.iloc[i] for i, (y, qq) in enumerate(zip(year, q)) if qq == 4}
    prev_fy = pd.Series([fy_by_year.get(int(y) - 1, float("nan")) for y in year], index=idx)
    return ytd + prev_fy - ytd.shift(4)


def build_quarterly(ticker: str) -> pd.DataFrame:
    cum = _cumulative_frame(ticker)
    out = pd.DataFrame(index=cum.index)

    # YTD nominal levels
    for m in _LEVELS:
        if m in cum.columns:
            out[f"{m}_ytd"] = cum[m]

    # margins on YTD (primary, inflation-neutral)
    for name, (num, den) in C.MARGIN_METRICS.items():
        if num in cum.columns and den in cum.columns:
            out[name] = cum[num] / cum[den] * 100.0

    # clean YoY: current YTD vs same-quarter prior-year YTD
    for m in ["net_sales", "net_profit", "ebitda"]:
        if m in cum.columns:
            out[f"{m}_ytd_yoy"] = (cum[m] / cum[m].shift(4) - 1.0) * 100.0

    # robust TTM level + real-TRY TTM
    defl = quarterly_deflators().reindex(cum.index)
    cpi = quarterly_cpi_index().reindex(cum.index)
    out["deflator"] = defl
    out["cpi_index"] = cpi
    if "net_sales" in cum.columns:
        out["net_sales_ttm"] = _ttm(cum["net_sales"])
        out["net_sales_ttm_real"] = out["net_sales_ttm"] * out["deflator"]

    # total assets snapshot (best-effort)
    try:
        ta = _pick_rows(_load_statement(ticker, "balance"), C.BALANCE_MAP).astype(float)
        if "total_assets" in ta.columns:
            out["total_assets"] = ta["total_assets"].reindex(out.index)
    except (FileNotFoundError, KeyError, ValueError):
        pass

    out = out.loc[out.index.isin(C.QUARTERS)].copy()
    out.insert(0, "company", ticker)
    out.insert(1, "company_name", C.COMPANIES[ticker])
    out.index.name = "quarter"
    return out.reset_index()


def build_annual(ticker: str) -> pd.DataFrame:
    """FY = Q4 YTD; nominal + real-TRY (base-quarter prices) + YoY."""
    cum = _cumulative_frame(ticker)
    defl = quarterly_deflators()
    q4 = cum.loc[cum.index.str.endswith("Q4")].copy()
    q4["year"] = q4.index.str.slice(0, 4).astype(int)
    q4 = q4[q4["year"].between(C.START_YEAR, C.END_YEAR)]

    rows = []
    for _, r in q4.iterrows():
        yr = int(r["year"])
        d = float(defl.get(f"{yr}Q4", float("nan")))
        rec = {"company": ticker, "company_name": C.COMPANIES[ticker], "year": yr,
               "deflator": d}
        for m in _LEVELS:
            if m in cum.columns:
                rec[f"{m}_fy"] = r[m]
                rec[f"{m}_fy_real"] = r[m] * d
        if {"gross_profit", "net_sales"} <= set(cum.columns):
            rec["gross_margin_fy"] = r["gross_profit"] / r["net_sales"] * 100
            rec["operating_margin_fy"] = r["operating_profit"] / r["net_sales"] * 100
            rec["net_margin_fy"] = r["net_profit"] / r["net_sales"] * 100
            if "ebitda" in cum.columns:
                rec["ebitda_margin_fy"] = r["ebitda"] / r["net_sales"] * 100
        rows.append(rec)

    df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    df["net_sales_fy_yoy_nominal"] = df["net_sales_fy"].pct_change() * 100
    df["net_sales_fy_yoy_real"] = df["net_sales_fy_real"].pct_change() * 100
    return df


def build_discrete_reference(ticker: str) -> pd.DataFrame:
    """Discrete quarters — REFERENCE ONLY (unreliable under TMS 29; see module docstring)."""
    disc = decumulate(_cumulative_frame(ticker))
    disc = disc.loc[disc.index.isin(C.QUARTERS)].copy()
    disc.columns = [f"disc_{c}" for c in disc.columns]
    disc.insert(0, "company", ticker)
    disc.index.name = "quarter"
    return disc.reset_index()


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def build_all(tickers: list[str] | None = None) -> dict[str, pd.DataFrame]:
    tickers = tickers or C.TICKERS
    C.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    quarterly = pd.concat([build_quarterly(t) for t in tickers], ignore_index=True)
    annual = pd.concat([build_annual(t) for t in tickers], ignore_index=True)
    discrete = pd.concat([build_discrete_reference(t) for t in tickers], ignore_index=True)

    quarterly = quarterly.sort_values(["company", "quarter"]).reset_index(drop=True)
    quarterly.to_csv(C.DATA_PROCESSED / "quarterly_panel.csv", index=False, encoding="utf-8")
    annual.to_csv(C.DATA_PROCESSED / "annual_panel.csv", index=False, encoding="utf-8")
    discrete.to_csv(C.DATA_PROCESSED / "quarterly_discrete_reference.csv",
                    index=False, encoding="utf-8")
    for name, df in [("quarterly_panel", quarterly), ("annual_panel", annual)]:
        try:
            df.to_parquet(C.DATA_PROCESSED / f"{name}.parquet", index=False)
        except Exception:
            pass
    return {"quarterly": quarterly, "annual": annual, "discrete": discrete}


if __name__ == "__main__":
    res = build_all()
    q, a = res["quarterly"], res["annual"]
    print(f"quarterly_panel: {q.shape[0]} rows ({q['company'].nunique()}x{q['quarter'].nunique()})")
    print(f"annual_panel   : {a.shape[0]} rows\n")
    cols = ["company", "quarter", "gross_margin", "operating_margin", "net_margin",
            "ebitda_margin", "net_sales_ttm_real", "net_sales_ytd_yoy"]
    with pd.option_context("display.width", 200, "display.float_format", lambda v: f"{v:,.2f}"):
        print(q[q.company == "MGROS"][cols].to_string(index=False))
        print("\nAnnual real-TRY net sales (base 2025Q4, billions):")
        piv = a.assign(real_B=(a["net_sales_fy_real"] / 1e9).round(1)).pivot(
            index="year", columns="company", values="real_B")
        print(piv.to_string())
    print("\nCoverage (non-null):")
    for m in ["gross_margin", "operating_margin", "net_margin", "ebitda_margin",
              "net_sales_ttm_real", "total_assets"]:
        print(f"  {m:20s} {int(q[m].notna().sum())}/{len(q)}")
