

from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile
import re
from typing import Dict, Optional

_NUMBER_RX = re.compile(r"[-+]?\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?|[-+]?\d+(?:\.\d+)?")
_TAG_VALUE_RX = re.compile(r">\s*([^<]+)\s*<")

# Tag synonyms (order matters: earlier = higher priority)
PL_TAGS = {
    "Revenue": [
        "ifrs-full:Revenue",
        "jppfs_cor:NetSales",
        "jpdei_cor:NetSales",
        "NetSales",
        "Revenue",
    ],
    "OperatingIncome": [
        "jppfs_cor:OperatingIncome",
        "ifrs-full:ProfitLossFromOperatingActivities",
        "OperatingIncome",
        "OperatingProfit",
    ],
    "NetIncome": [
        "jppfs_cor:ProfitAttributableToOwnersOfParent",
        "ifrs-full:ProfitLoss",
        "NetIncome",
        "Profit",
        "ProfitLoss",
    ],
    "GrossProfit": [
        "jppfs_cor:GrossProfit",
        "ifrs-full:GrossProfit",
        "GrossProfit",
    ],
}

BS_TAGS = {
    "Assets": ["ifrs-full:Assets", "jppfs_cor:Assets", "Assets", "TotalAssets"],
    "Liabilities": ["ifrs-full:Liabilities", "jppfs_cor:Liabilities", "Liabilities", "TotalLiabilities"],
    "Equity": [
        "ifrs-full:Equity",
        "jppfs_cor:Equity",
        "Equity",
        "EquityAttributableToOwnersOfParent",
        "ShareholdersEquity",
        "NetAssets",
    ],
}

CF_TAGS = {
    "OperatingCF": [
        "ifrs-full:NetCashFlowsFromUsedInOperatingActivities",
        "jppfs_cor:NetCashProvidedByUsedInOperatingActivities",
        "OperatingCF",
    ],
    "InvestingCF": [
        "ifrs-full:NetCashFlowsFromUsedInInvestingActivities",
        "jppfs_cor:NetCashProvidedByUsedInInvestingActivities",
        "InvestingCF",
    ],
    "FinancingCF": [
        "ifrs-full:NetCashFlowsFromUsedInFinancingActivities",
        "jppfs_cor:NetCashProvidedByUsedInFinancingActivities",
        "FinancingCF",
    ],
    "Cash": [
        "ifrs-full:CashAndCashEquivalents",
        "jppfs_cor:CashAndCashEquivalents",
        "CashAndCashEquivalents",
        "Cash",
    ],
}

PERIOD_TAGS = [
    "jpdei_cor:DocumentPeriodEndDate",
    "jppfs_cor:CurrentFiscalYearEndDate",
    "ifrs-full:ReportingPeriodEndDate",
    "dei:DocumentPeriodEndDate",
]


def _to_float(s: str) -> Optional[float]:
    if not s:
        return None
    m = _NUMBER_RX.search(s.replace("\u00a0", " "))
    if not m:
        return None
    val = m.group(0).replace(",", "").replace(" ", "")
    try:
        return float(val)
    except Exception:
        return None


def _extract_first(xml: str, tag_names: list[str]) -> Optional[float]:
    for t in tag_names:
        # capture text value between >...< for any element matching local/qualified name
        pat_open = re.compile(rf"<[^:]*:?{re.escape(t.split(':')[-1])}[^>]*>", re.IGNORECASE)
        for m in pat_open.finditer(xml):
            # slice forward to the closing angle and read following text until '<'
            start = m.end()
            mval = _TAG_VALUE_RX.search(xml, start)
            if mval:
                v = _to_float(mval.group(1))
                if v is not None:
                    return v
    return None


def _extract_period(xml: str) -> str:
    for t in PERIOD_TAGS:
        pat = re.compile(rf"<[^:]*:?{re.escape(t.split(':')[-1])}[^>]*>\s*([^<]+)\s*<", re.IGNORECASE)
        m = pat.search(xml)
        if m:
            raw = m.group(1).strip()
            # Normalize to FYyyyy if possible
            y = re.search(r"(20\d{2}|19\d{2})", raw)
            if y:
                return f"FY{y.group(1)}"
            return raw
    # fallback: try find any 4-digit year
    y = re.search(r"(20\d{2}|19\d{2})", xml)
    return f"FY{y.group(1)}" if y else ""


def parse_xbrl_zip(zip_path: Path) -> Dict[str, dict]:
    """
    Best-effort parser for EDINET XBRL ZIP.
    Returns dict with keys: period (str), PL/BS/CF (dicts of floats or None).
    Safe on malformed ZIP/XBRL (returns None-valued structure).
    """
    pl: Dict[str, Optional[float]] = {k: None for k in PL_TAGS}
    bs: Dict[str, Optional[float]] = {k: None for k in BS_TAGS}
    cf: Dict[str, Optional[float]] = {k: None for k in CF_TAGS}
    period: str = ""

    try:
        with ZipFile(zip_path) as z:
            # Prefer .xbrl/.xml
            xbrl_names = [n for n in z.namelist() if n.lower().endswith((".xbrl", ".xml"))]
            for name in xbrl_names:
                try:
                    xml = z.read(name).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                if not period:
                    period = _extract_period(xml)
                # Fill PL/BS/CF if missing
                for k, tags in PL_TAGS.items():
                    if pl[k] is None:
                        pl[k] = _extract_first(xml, tags)
                for k, tags in BS_TAGS.items():
                    if bs[k] is None:
                        bs[k] = _extract_first(xml, tags)
                for k, tags in CF_TAGS.items():
                    if cf[k] is None:
                        cf[k] = _extract_first(xml, tags)
                # Stop early if we have a decent set
                if any(pl.values()) and any(bs.values()):
                    break
    except Exception:
        # fall through to safe default return
        pass

    return {
        "period": period or "",
        "PL": pl,
        "BS": bs,
        "CF": cf,
    }
