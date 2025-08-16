
from fastapi import APIRouter, Query, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import List, Optional
from datetime import date
from core.config import get_settings
from services.sources_service import jq_statements, edinet_parse
from ingestion.edinet_downloader import list_filings_by_date, list_filings_range

router = APIRouter(tags=["sources"])
security = HTTPBasic()


def _auth(creds: HTTPBasicCredentials = Depends(security)):
    s = get_settings()
    if creds.username != s.API_USER or creds.password != s.API_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})


@router.get("/jq/statements")
def jq_statements_api(code: str, period: str = Query("fy"), _: str = Depends(_auth)):
    try:
        return {"code": code, "period": period, "statements": jq_statements(code, period=period)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"J-Quants fetch failed: {e}")


@router.get("/edinet/list")
def edinet_list_api(
    _: str = Depends(_auth),
    date_str: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD"),
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    edinet_code: Optional[str] = Query(None, description="E00001 など"),
    doc_type_codes: Optional[str] = Query(None, description="comma-separated e.g. 120,130"),
):
    # Validate mutually exclusive/date presence
    if date_str and (start or end):
        raise HTTPException(status_code=422, detail="Provide either date or start/end, not both")
    if (start and not end) or (end and not start):
        raise HTTPException(status_code=422, detail="start and end must be provided together")
    if not date_str and not (start and end):
        raise HTTPException(status_code=422, detail="date or start/end is required")

    def _parse_d(d: str) -> date:
        try:
            return date.fromisoformat(d)
        except Exception:
            raise HTTPException(status_code=422, detail=f"Invalid date format: {d}")

    codes: List[str] = [c.strip() for c in (doc_type_codes.split(',') if doc_type_codes else []) if c.strip()]

    try:
        if start and end:
            _ = _parse_d(start); _ = _parse_d(end)  # validation only
            return {"filings": list_filings_range(edinet_code or "", start, end, doc_type_codes=codes)}
        else:
            _ = _parse_d(date_str or "")
            return {"filings": list_filings_by_date(date_str, edinet_code=edinet_code, doc_type_codes=codes)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"EDINET list failed: {e}")


@router.get("/edinet/parse")
def edinet_parse_api(document_id: str, _: str = Depends(_auth)):
    try:
        return {"document_id": document_id, "parsed": edinet_parse(document_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"EDINET parse failed: {e}")
