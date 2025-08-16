from storage.db import SessionLocal
from storage.models import FinancialSnapshot
import re
from typing import Any, Dict, Optional


def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        # Allow strings like "1,234" or "1 234"
        if isinstance(x, str):
            x = x.replace(",", "").replace(" ", "")
        return float(x)
    except Exception:
        return None


def _pick(d: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        if k in d and d[k] is not None:
            return _to_float(d[k])
    return None


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    if b == 0:
        return None
    return a / b


_period_rx = re.compile(r"(?P<y>\d{4})(?:[-/ ]?Q(?P<q>[1-4]))?")


def _period_key(p: str):
    """Sort key for periods like '2023', '2023-Q4', '2023/ Q1'. Unknowns go last."""
    s = str(p)
    m = _period_rx.search(s)
    if not m:
        return (float("inf"), float("inf"))
    y = int(m.group("y"))
    q = int(m.group("q") or 0)
    return (y, q)


def compute_basic_ratios(company_id: str):
    """
    Compute core ratios as DECIMALS (e.g., 0.123 for 12.3%).
    Keys returned per row:
        period, OperatingMargin, NetMargin, ROE, ROA, EquityRatio, GrossMargin?, RevenueGrowth?
    """
    db = SessionLocal()
    try:
        snaps = (
            db.query(FinancialSnapshot)
            .filter(FinancialSnapshot.company_id == company_id)
            .all()
        )
        # Sort by parsed period
        snaps = sorted(snaps, key=lambda x: _period_key(x.period))

        series = []
        prev_revenue: Optional[float] = None
        for s in snaps:
            pl, bs = s.pl or {}, s.bs or {}

            revenue = _pick(pl, "Revenue", "NetSales", "Sales")
            op = _pick(pl, "OperatingIncome", "OperatingProfit", "OpIncome", "EBIT")
            net = _pick(
                pl,
                "NetIncome",
                "Profit",
                "NetProfit",
                "ProfitAttributableToOwners",
                "PAT",
            )
            gross = _pick(pl, "GrossProfit")

            assets = _pick(bs, "Assets", "TotalAssets")
            equity = _pick(
                bs,
                "Equity",
                "TotalEquity",
                "ShareholdersEquity",
                "EquityAttributableToOwners",
                "NetAssets",
            )

            operating_margin = _safe_div(op, revenue)  # decimal
            net_margin = _safe_div(net, revenue)  # decimal
            roe = _safe_div(net, equity)  # decimal
            roa = _safe_div(net, assets)  # decimal
            equity_ratio = _safe_div(equity, assets)  # decimal
            gross_margin = _safe_div(gross, revenue) if (gross is not None and revenue) else None

            revenue_growth = None
            if prev_revenue is not None and revenue is not None and prev_revenue != 0:
                revenue_growth = (revenue - prev_revenue) / prev_revenue  # decimal
            prev_revenue = revenue if revenue is not None else prev_revenue

            series.append(
                {
                    "period": s.period,
                    "OperatingMargin": operating_margin,
                    "NetMargin": net_margin,
                    "ROE": roe,
                    "ROA": roa,
                    "EquityRatio": equity_ratio,
                    **({"GrossMargin": gross_margin} if gross_margin is not None else {}),
                    **({"RevenueGrowth": revenue_growth} if revenue_growth is not None else {}),
                }
            )
        return series
    finally:
        db.close()
