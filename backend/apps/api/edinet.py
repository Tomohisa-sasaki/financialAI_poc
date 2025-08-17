# backend/apps/api/edinet.py
from fastapi import APIRouter, HTTPException, Query
from backend.parsing.edinet_parser_v2 import parse_financials_from_xbrl_bytes
from backend.ingestion.edinet_downloader import download_edinet_zip  # 既存のダウンロード関数を想定

router = APIRouter(prefix="/edinet", tags=["edinet"])

@router.get("/parse")
def parse_edinet(document_id: str = Query(..., alias="document_id")):
    try:
        zbytes = download_edinet_zip(document_id)  # bytes で返る想定
        parsed = parse_financials_from_xbrl_bytes(zbytes)
        return {"parsed": parsed}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析に失敗: {e}"[:200])
