from pathlib import Path
from datetime import datetime, timedelta
import requests
from tenacity import retry, wait_exponential, stop_after_attempt
from parsing.xbrl_parser import parse_xbrl_zip

DATA_DIR = Path("backend/data/raw/edinet")
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASE = "https://disclosure.edinet-fsa.go.jp/api/v2"
UA = {"User-Agent": "FinancialAI/1.0 (+backend/ingestion/edinet_downloader.py)"}

@retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
def _get_documents_json(date: str, edinet_code: str | None = None, page: int = 1):
    params = {"date": date, "type": 2, "pagenumber": page}
    if edinet_code:
        params["edinetCode"] = edinet_code
    r = requests.get(f"{BASE}/documents.json", params=params, timeout=60, headers=UA)
    r.raise_for_status()
    return r.json()

def list_filings_by_date(date: str, edinet_code: str | None = None, doc_type_codes: list[str] | None = None) -> list[dict]:
    page = 1; results = []
    while True:
        js = _get_documents_json(date, edinet_code=edinet_code, page=page)
        recs = js.get("results") or []
        if doc_type_codes:
            recs = [r for r in recs if str(r.get("docTypeCode")) in set(doc_type_codes)]
        results.extend(recs)
        if not js.get("hasNextPage") or len(recs) == 0: break
        page += 1
        if page > 30: break
    return results

def list_filings_range(edinet_code: str, start_date: str, end_date: str, doc_type_codes: list[str] | None = None) -> list[dict]:
    d0 = datetime.strptime(start_date, "%Y-%m-%d").date()
    d1 = datetime.strptime(end_date, "%Y-%m-%d").date()
    out, cur = [], d0
    while cur <= d1:
        out.extend(list_filings_by_date(cur.isoformat(), edinet_code=edinet_code, doc_type_codes=doc_type_codes))
        cur += timedelta(days=1)
    return out

@retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
def _download_zip(document_id: str) -> Path:
    p = DATA_DIR / f"{document_id}.zip"
    if p.exists(): return p
    r = requests.get(f"{BASE}/documents/{document_id}", params={"type": 1}, timeout=90, headers=UA)
    r.raise_for_status()
    p.write_bytes(r.content)
    return p

def parse_document(document_id: str):
    z = _download_zip(document_id)
    # 例外は上位で個別スキップするためここでは送出
    return parse_xbrl_zip(z)

def get_latest_financials_from_edinet_by_code(edinet_code: str, start_date: str, end_date: str):
    filings = list_filings_range(edinet_code, start_date, end_date)
    out: list[dict] = []
    for f in filings:
        doc_id = f.get("docID") or f.get("docId")
        if not doc_id:
            continue
        try:
            parsed = parse_document(doc_id)
        except Exception:
            # 解析失敗のドキュメントは安全にスキップ
            continue
        out.append({
            "period": parsed.get("period", ""),
            "pl": parsed.get("PL", {}),
            "bs": parsed.get("BS", {}),
            "cf": parsed.get("CF", {}),
            "raw": {"documentId": doc_id}
        })
    out.sort(key=lambda x: x.get("period", ""), reverse=True)
    return out
