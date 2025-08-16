
from __future__ import annotations
from typing import Any, Optional, Dict
from storage.db import SessionLocal
from storage.models import FinancialSnapshot


def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, str):
            x = x.replace(",", "").replace(" ", "")
        return float(x)
    except Exception:
        return None


def _pick(d: dict, *keys: str) -> Optional[float]:
    for k in keys:
        if k in d and d[k] is not None:
            v = _to_float(d[k])
            if v is not None:
                return v
    return None


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return a / b


# Canonicalization for input metric ids
_CANON = {
    # percentage/ratio (decimals)
    "ROE": "ROE",
    "ROA": "ROA",
    "OPERATINGMARGIN": "OperatingMargin",
    "OPERATING_MARGIN": "OperatingMargin",
    "NETMARGIN": "NetMargin",
    "NET_MARGIN": "NetMargin",
    "EQUITYRATIO": "EquityRatio",
    "EQUITY_RATIO": "EquityRatio",
    "GROSSMARGIN": "GrossMargin",
    "GROSS_MARGIN": "GrossMargin",
    # raw values
    "REVENUE": "Revenue",
    "OPERATINGINCOME": "OperatingIncome",
    "NETINCOME": "NetIncome",
    # growth
    "REVENUE_GROWTH": "RevenueGrowth",
}


def _metric_value(m: str, pl: dict, bs: dict, prev: Dict[str, float] | None = None) -> Optional[float]:
    rev = _pick(pl, "Revenue", "NetSales", "Sales")
    op = _pick(pl, "OperatingIncome", "OperatingProfit", "EBIT")
    net = _pick(pl, "NetIncome", "Profit", "NetProfit", "ProfitAttributableToOwners")
    assets = _pick(bs, "Assets", "TotalAssets")
    equity = _pick(bs, "Equity", "TotalEquity", "ShareholdersEquity", "NetAssets")

    if m == "ROE":
        return _safe_div(net, equity)
    if m == "ROA":
        return _safe_div(net, assets)
    if m == "OperatingMargin":
        return _safe_div(op, rev)
    if m == "NetMargin":
        return _safe_div(net, rev)
    if m == "EquityRatio":
        return _safe_div(equity, assets)
    if m == "GrossMargin":
        gross = _pick(pl, "GrossProfit")
        return _safe_div(gross, rev)
    if m == "Revenue":
        return rev
    if m == "OperatingIncome":
        return op
    if m == "NetIncome":
        return net
    if m == "RevenueGrowth":
        # uses prev["Revenue"] if present
        prev_rev = (prev or {}).get("Revenue")
        if prev_rev is not None and prev_rev != 0 and rev is not None:
            return (rev - prev_rev) / prev_rev
        return None
    return None


def calc_metrics(company_ids: list[str], metric_ids: list[str], period: str = "fy"):
    db = SessionLocal()
    try:
        out = {cid: {} for cid in company_ids}
        canon_metrics = [_CANON.get(m.upper(), m) for m in metric_ids]

        for cid in company_ids:
            snaps = db.query(FinancialSnapshot).filter(FinancialSnapshot.company_id == cid).all()
            snaps = sorted(snaps, key=lambda s: str(s.period))

            # Pre-compute revenue per period for growth calc
            rev_by_period: Dict[str, float] = {}
            for s in snaps:
                r = _pick((s.pl or {}), "Revenue", "NetSales", "Sales")
                if r is not None:
                    rev_by_period[str(s.period)] = r

            for m in canon_metrics:
                series = {}
                prev_cache = {"Revenue": None}
                for s in snaps:
                    pl, bs = (s.pl or {}), (s.bs or {})
                    val = _metric_value(m, pl, bs, prev_cache)
                    if val is not None:
                        series[str(s.period)] = float(val)
                    # update prev revenue for growth
                    rv = _pick(pl, "Revenue", "NetSales", "Sales")
                    if rv is not None:
                        prev_cache["Revenue"] = rv
                out[cid][m] = series
        return out
    finally:
        db.close()
