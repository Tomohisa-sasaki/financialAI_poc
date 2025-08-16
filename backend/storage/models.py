from sqlalchemy import Column, Integer, String, JSON, UniqueConstraint, Index
from .db import Base


class CompanyRef(Base):
    __tablename__ = "company_ref"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String, index=True)
    name = Column(String, index=True)
    edinet_code = Column(String, index=True)
    jq_code = Column(String, index=True)

    __table_args__ = (
        # 企業IDとコードの複合検索を高速化
        Index("idx_company_ref_company_edinet", "company_id", "edinet_code"),
        Index("idx_company_ref_company_jq", "company_id", "jq_code"),
    )

    def __repr__(self) -> str:  # debug-friendly
        return f"<CompanyRef company_id={self.company_id} edinet={self.edinet_code} jq={self.jq_code}>"


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshot"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String, index=True)
    period = Column(String, index=True)  # e.g., FY2023 / 2024-Q4
    pl = Column(JSON)
    bs = Column(JSON)
    cf = Column(JSON)
    source = Column(String, index=True)  # jquants / edinet

    __table_args__ = (
        # 会社×期間×ソースでユニーク（重複投入防止）
        UniqueConstraint("company_id", "period", "source", name="_uniq_company_period_source"),
        # 会社×期間の時系列取得を高速化（source非依存の集計にも有効）
        Index("idx_financial_snapshot_company_period", "company_id", "period"),
    )

    def __repr__(self) -> str:
        return f"<FinancialSnapshot company_id={self.company_id} period={self.period} source={self.source}>"
