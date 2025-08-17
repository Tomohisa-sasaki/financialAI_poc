# backend/tests/test_edinet_parser_v2.py
from backend.parsing.edinet_parser_v2 import parse_financials_from_xbrl_bytes

def test_parse_ixbrl_minimal():
    # 最小限の iXBRL（コンテキスト1個＋主要4項目）
    ix = b'''<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
                   xmlns:xbrli="http://www.xbrl.org/2003/instance">
      <xbrli:context id="C1">
        <xbrli:entity><xbrli:identifier scheme="http://example.com">E</xbrli:identifier></xbrli:entity>
        <xbrli:period><xbrli:startDate>2023-04-01</xbrli:startDate><xbrli:endDate>2024-03-31</xbrli:endDate></xbrli:period>
      </xbrli:context>

      <!-- PL -->
      <ix:nonFraction name="jppfs_cor:NetSales" contextRef="C1">1,234</ix:nonFraction>
      <ix:nonFraction name="jppfs_cor:OperatingIncome" contextRef="C1">(567)</ix:nonFraction>

      <!-- BS -->
      <ix:nonFraction name="jppfs_cor:Assets" contextRef="C1">10000</ix:nonFraction>

      <!-- CF -->
      <ix:nonFraction name="jppfs_cor:NetCashProvidedByUsedInOperatingActivities" contextRef="C1">900</ix:nonFraction>
    </html>'''
    res = parse_financials_from_xbrl_bytes(ix)
    assert isinstance(res, dict)
    assert "PL" in res and "BS" in res and "CF" in res

    # 値チェック（カンマ削除・括弧負号対応）
    assert res["PL"]["売上高"] == 1234.0
    assert res["PL"]["営業利益"] == -567.0
    assert res["BS"]["総資産"] == 10000.0
    assert res["CF"]["営業CF"] == 900.0
