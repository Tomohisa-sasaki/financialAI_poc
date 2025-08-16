
from __future__ import annotations
from typing import Dict
from loguru import logger
from storage.db import SessionLocal
from storage.models import FinancialSnapshot, CompanyRef
from ingestion.jquants_downloader import get_statements
from ingestion.edinet_downloader import get_latest_financials_from_edinet_by_code


_DEF_START = "2023-01-01"
_DEF_END = "2025-12-31"


def _key(period: str, source: str) -> tuple[str, str]:
    return (str(period or ""), str(source or ""))


def get_financials(company_id: str, period: str = "fy", source: str = "auto") -> Dict[str, Dict[str, int]]:
    """Ingest financials from J-Quants and EDINET into FinancialSnapshot.

    Returns: {"status": "ok", "inserted": {"jquants": int, "edinet": int}}
    """
    db = SessionLocal()
    inserted = {"jquants": 0, "edinet": 0}
    try:
        cached = db.query(FinancialSnapshot).filter(FinancialSnapshot.company_id == company_id).all()
        existing = {(_key(c.period, c.source)) for c in cached}

        # --- J-Quants ---
        try:
            jq = get_statements(company_id, period=period) or []
        except Exception as e:
            logger.warning(f"J-Quants get_statements failed for {company_id}: {e}")
            jq = []
        for it in jq:
            k = _key(it.get("period", ""), "jquants")
            if k not in existing:
                db.add(
                    FinancialSnapshot(
                        company_id=company_id,
                        period=it.get("period", ""),
                        pl=it.get("pl", {}),
                        bs=it.get("bs", {}),
                        cf=it.get("cf", {}),
                        source="jquants",
                    )
                )
                existing.add(k)
                inserted["jquants"] += 1

        # --- EDINET ---
        ed_code = None
        try:
            cref = db.query(CompanyRef).filter(CompanyRef.company_id == company_id).first()
            ed_code = getattr(cref, "edinet_code", None) if cref else None
        except Exception as e:
            logger.debug(f"CompanyRef lookup failed for {company_id}: {e}")
            ed_code = None
        if ed_code:
            try:
                ed = get_latest_financials_from_edinet_by_code(ed_code, start_date=_DEF_START, end_date=_DEF_END) or []
            except Exception as e:
                logger.warning(f"EDINET fetch failed for {ed_code}: {e}")
                ed = []
            for it in ed:
                k = _key(it.get("period", ""), "edinet")
                if k not in existing:
                    db.add(
                        FinancialSnapshot(
                            company_id=company_id,
                            period=it.get("period", ""),
                            pl=it.get("pl", {}),
                            bs=it.get("bs", {}),
                            cf=it.get("cf", {}),
                            source="edinet",
                        )
                    )
                    existing.add(k)
                    inserted["edinet"] += 1

        if any(inserted.values()):
            db.commit()
        else:
            db.rollback()  # noop but ensures clean state
        return {"status": "ok", "inserted": inserted}
    except Exception as e:
        db.rollback()
        logger.exception(f"get_financials failed for {company_id}")
        raise
    finally:
        db.close()
