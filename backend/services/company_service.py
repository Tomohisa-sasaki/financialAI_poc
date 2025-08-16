
from storage.db import SessionLocal
from storage.models import CompanyRef

SEED = [
    {"company_id":"7203", "name":"トヨタ自動車", "edinet_code":"E02144", "jq_code":"72030"},
    {"company_id":"6758", "name":"ソニーグループ", "edinet_code":"E05714", "jq_code":"67580"},
    {"company_id":"7974", "name":"任天堂", "edinet_code":"E02367", "jq_code":"79740"},
    {"company_id":"9984", "name":"ソフトバンクG", "edinet_code":"E02778", "jq_code":"99840"},
]

def ensure_seed():
    db = SessionLocal()
    try:
        for c in SEED:
            ex = db.query(CompanyRef).filter(CompanyRef.company_id==c["company_id"]).first()
            if not ex:
                db.add(CompanyRef(**c))
        db.commit()
    finally:
        db.close()

def search_companies(q: str):
    db = SessionLocal()
    try:
        ql = q.strip().lower()
        rows = db.query(CompanyRef).all()
        out = []
        for r in rows:
            if ql in r.company_id.lower() or ql in r.name.lower():
                out.append({"id": r.company_id, "name": r.name, "edinet_code": r.edinet_code, "jq_code": r.jq_code})
        return out
    finally:
        db.close()


from __future__ import annotations
from typing import List, Dict
from sqlalchemy import or_
from storage.db import SessionLocal
from storage.models import CompanyRef

SEED: List[Dict[str, str]] = [
    {"company_id": "7203", "name": "トヨタ自動車", "edinet_code": "E02144", "jq_code": "72030"},
    {"company_id": "6758", "name": "ソニーグループ", "edinet_code": "E05714", "jq_code": "67580"},
    {"company_id": "7974", "name": "任天堂", "edinet_code": "E02367", "jq_code": "79740"},
    {"company_id": "9984", "name": "ソフトバンクG", "edinet_code": "E02778", "jq_code": "99840"},
]


def ensure_seed() -> None:
    """Insert or update seed companies idempotently."""
    db = SessionLocal()
    try:
        for c in SEED:
            ex = db.query(CompanyRef).filter(CompanyRef.company_id == c["company_id"]).first()
            if ex:
                # Update sparse fields if changed
                updated = False
                for k in ("name", "edinet_code", "jq_code"):
                    v = c.get(k)
                    if v and getattr(ex, k) != v:
                        setattr(ex, k, v)
                        updated = True
                if updated:
                    db.add(ex)
            else:
                db.add(CompanyRef(**c))
        db.commit()
    finally:
        db.close()


def search_companies(q: str, limit: int = 20):
    """Lightweight search with ranking.

    - 前方一致 > 部分一致 > ID完全一致以外の弱一致
    - company_id / name の両方を対象
    - limit は最終返却件数（内部的には広めに拾ってからスコアで絞り込み）
    """
    q = (q or "").strip()
    if not q:
        return []
    ql = q.lower()

    db = SessionLocal()
    try:
        # まずは LIKE で候補を絞る（全件走査を回避）
        candidates = (
            db.query(CompanyRef)
            .filter(
                or_(
                    CompanyRef.company_id.ilike(f"%{ql}%"),
                    CompanyRef.name.ilike(f"%{ql}%"),
                )
            )
            .limit(max(limit * 3, 50))
            .all()
        )

        def score(row: CompanyRef) -> int:
            id_l = (row.company_id or "").lower()
            nm_l = (row.name or "").lower()
            s = 0
            if ql == id_l or ql == nm_l:
                s += 100  # 完全一致
            if id_l.startswith(ql) or nm_l.startswith(ql):
                s += 50   # 前方一致
            if ql in id_l or ql in nm_l:
                s += 10   # 部分一致
            return s

        ranked = sorted(candidates, key=score, reverse=True)[:limit]
        return [
            {
                "id": r.company_id,
                "name": r.name,
                "edinet_code": r.edinet_code,
                "jq_code": r.jq_code,
            }
            for r in ranked
        ]
    finally:
        db.close()