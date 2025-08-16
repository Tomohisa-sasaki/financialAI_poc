
from __future__ import annotations
from typing import Dict, Any
from ingestion.jquants_downloader import get_statements
from ingestion.edinet_downloader import parse_document


def jq_statements(code: str, period: str = "fy") -> Dict[str, Any]:
    code = (code or "").strip()
    if not code:
        return {"ok": False, "error": "code is required", "statements": []}
    try:
        data = get_statements(code, period=period) or []
        return {"ok": True, "code": code, "period": period, "statements": data}
    except Exception as e:
        return {"ok": False, "error": str(e), "statements": []}


def edinet_parse(document_id: str) -> Dict[str, Any]:
    document_id = (document_id or "").strip()
    if not document_id:
        return {"ok": False, "error": "document_id is required", "parsed": {}}
    try:
        parsed = parse_document(document_id) or {}
        return {"ok": True, "document_id": document_id, "parsed": parsed}
    except Exception as e:
        return {"ok": False, "error": str(e), "parsed": {}}
