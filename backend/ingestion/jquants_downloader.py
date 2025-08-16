import time
from typing import Optional, Dict, Any, List
import requests
from tenacity import retry, wait_exponential, stop_after_attempt
from core.config import get_settings

BASE = "https://api.jquants.com/v1"
UA = {"User-Agent": "FinancialAI/1.0 (+backend/ingestion/jquants_downloader.py)"}

# Simple in-process cache for idToken
_ID_TOKEN: Optional[str] = None
_ID_TOKEN_TS: float = 0.0
_ID_TOKEN_TTL = 600.0  # seconds


@retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
def _post(url: str, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {}) or {}
    headers = {**UA, **headers}
    return requests.post(url, timeout=20, headers=headers, **kwargs)


@retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
def _get(url: str, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {}) or {}
    headers = {**UA, **headers}
    return requests.get(url, timeout=20, headers=headers, **kwargs)


def _fetch_id_token() -> Optional[str]:
    """Retrieve and cache idToken. Prefer refresh token if provided."""
    global _ID_TOKEN, _ID_TOKEN_TS
    now = time.time()
    if _ID_TOKEN and (now - _ID_TOKEN_TS) < _ID_TOKEN_TTL:
        return _ID_TOKEN

    s = get_settings()
    try:
        # 1) Use preset refresh token if available
        if s.JQ_REFRESH_TOKEN:
            r = _post(f"{BASE}/token/auth_refresh", params={"refreshtoken": s.JQ_REFRESH_TOKEN})
            r.raise_for_status()
            tok = (r.json() or {}).get("idToken")
            if tok:
                _ID_TOKEN = tok
                _ID_TOKEN_TS = now
                return tok
        # 2) Fallback to email/password
        if s.JQ_EMAIL and s.JQ_PASSWORD:
            r1 = _post(
                f"{BASE}/token/auth_user",
                json={"mailaddress": s.JQ_EMAIL, "password": s.JQ_PASSWORD},
            )
            r1.raise_for_status()
            refresh = (r1.json() or {}).get("refreshToken")
            if refresh:
                r2 = _post(f"{BASE}/token/auth_refresh", params={"refreshtoken": refresh})
                r2.raise_for_status()
                tok = (r2.json() or {}).get("idToken")
                if tok:
                    _ID_TOKEN = tok
                    _ID_TOKEN_TS = now
                    return tok
    except Exception:
        return None
    return None


def _api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[dict]:
    tok = _fetch_id_token()
    if not tok:
        return None
    try:
        r = _get(f"{BASE}{path}", params=params or {}, headers={"Authorization": f"Bearer {tok}"})
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def get_statements(company_id: str, period: str = "fy") -> List[Dict[str, Any]]:
    """
    Return normalized statements for a company. If J-Quants API credentials are not
    configured/valid, return demo data (backward-compatible).

    NOTE: Real API mapping to PL/BS/CF should be implemented here once schema is finalized.
    This stub keeps the interface stable for the rest of the app.
    """
    id_token = _fetch_id_token()
    if not id_token:
        # Fallback demo data for dev/preview
        return [
            {
                "period": "FY2023",
                "pl": {"Revenue": 100000, "OperatingIncome": 12000, "NetIncome": 9000},
                "bs": {"Assets": 300000, "Liabilities": 120000, "Equity": 180000},
                "cf": {"OperatingCF": 15000, "InvestingCF": -5000, "FinancingCF": -3000, "Cash": 25000},
            },
            {
                "period": "FY2022",
                "pl": {"Revenue": 95000, "OperatingIncome": 10000, "NetIncome": 8000},
                "bs": {"Assets": 280000, "Liabilities": 110000, "Equity": 170000},
                "cf": {"OperatingCF": 13000, "InvestingCF": -6000, "FinancingCF": -2000, "Cash": 22000},
            },
        ]

    # --- TODO: Implement actual mapping to your normalized schema ---
    # Example (pseudo):
    # js_pl = _api_get("/securities/finance/pl", params={"code": company_id, "period": period})
    # js_bs = _api_get("/securities/finance/bs", params={"code": company_id, "period": period})
    # js_cf = _api_get("/securities/finance/cf", params={"code": company_id, "period": period})
    # ...normalize to your {period, pl, bs, cf} list...
    # If any API returns None or raises, return [] to signal no live data yet.

    return []
