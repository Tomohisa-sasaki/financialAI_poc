# backend/parsing/edinet_parser_v2.py
from __future__ import annotations
import io, re, zipfile
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List, Iterable, Union
from lxml import etree

# ===== 基本ユーティリティ =====
_ZEN2HAN = str.maketrans("０１２３４５６７８９－，．％", "0123456789- ,.%")
_UNIT_RX = re.compile(r"(百万円|千円|万円|円|％|%|percent|JPY|iso4217:JPY)", re.I)
_PAREN_NEG_RX = re.compile(r"^\s*\((.+)\)\s*$")

def _zen2han(s: str) -> str:
    return (s or "").translate(_ZEN2HAN)

def _to_float(raw) -> Optional[float]:
    if raw is None: return None
    if isinstance(raw, (int, float)): return float(raw)
    s = _zen2han(str(raw)).strip()
    m = _PAREN_NEG_RX.match(s)
    sign = -1.0 if m else 1.0
    if m: s = m.group(1)
    s = s.replace(",", "")
    try:
        return sign * float(s)
    except Exception:
        return None

def _is_percent(text: str) -> bool:
    t = (text or "").lower()
    return ("％" in t) or ("%" in t) or ("percent" in t) or ("pure" in t and "ratio" in t)

def _infer_unit_multiplier(text: str) -> float:
    # ラベル/単位/タグ断片から倍率を推定
    t = (text or "")
    if re.search(r"百万円", t): return 100 * 1_000_000
    if re.search(r"千円", t):   return 1_000
    if re.search(r"万円", t):   return 10_000
    if re.search(r"円|JPY|iso4217:JPY", t, re.I): return 1.0
    return 1.0  # shares/pure 等は 1.0（％は別処理）

def _norm_key(s: str) -> str:
    return re.sub(r"[\s_\-‐・:：/\\()（）]+", "", _zen2han(s).lower())

# ===== タクソノミー（同義語マップ） =====
CANON = {
    # PL
    "revenue": ["売上高","売上","営業収益","sales","revenue","net sales"],
    "operating_income": ["営業利益","operating income","operating profit"],
    "net_income": ["当期純利益","純利益","profit attributable","net income","当期利益"],
    # BS
    "total_assets": ["総資産","total assets"],
    "net_assets": ["純資産","株主資本","net assets","equity"],
    "equity_ratio_pct": ["自己資本比率","equity ratio","自己資本比率（％）","自己資本比率(%)"],
    # CF
    "cfo": ["営業活動によるキャッシュフロー","営業cf","cash flows from operating","cfo"],
    "cfi": ["投資活動によるキャッシュフロー","投資cf","cash flows from investing","cfi"],
    "cff": ["財務活動によるキャッシュフロー","財務cf","cash flows from financing","cff"],
}

TAG2CANON = {
    # PL
    "jppfs_cor:NetSales": "revenue",
    "jppfs_cor:OperatingIncome": "operating_income",
    "jppfs_cor:ProfitLoss": "net_income",
    "jppfs_cor:ProfitAttributableToOwnersOfParent": "net_income",
    # BS
    "jppfs_cor:Assets": "total_assets",
    "jppfs_cor:Equity": "net_assets",
    # CF
    "jppfs_cor:NetCashProvidedByUsedInOperatingActivities": "cfo",
    "jppfs_cor:NetCashProvidedByUsedInInvestingActivities": "cfi",
    "jppfs_cor:NetCashProvidedByUsedInFinancingActivities": "cff",
}

CANON2SECTION = {
    "revenue":"PL","operating_income":"PL","net_income":"PL",
    "total_assets":"BS","net_assets":"BS","equity_ratio_pct":"BS",
    "cfo":"CF","cfi":"CF","cff":"CF",
}

# ===== XBRL / iXBRL ロード =====
NS = {
    "xbrli": "http://www.xbrl.org/2003/instance",
    "ix":    "http://www.xbrl.org/2013/inlineXBRL",
}

def _parse_any_xbrl(raw: bytes) -> etree._ElementTree:
    try:
        return etree.parse(io.BytesIO(raw))
    except etree.XMLSyntaxError:
        parser = etree.HTMLParser()
        return etree.parse(io.BytesIO(raw), parser)

def _load_xbrl_from_zip(zbytes: bytes) -> etree._ElementTree:
    with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
        names = [n for n in zf.namelist() if n.endswith(".xbrl")]
        if not names:
            names = [n for n in zf.namelist() if n.lower().endswith((".htm",".html"))]
        if not names:
            raise ValueError("XBRL/iXBRL ファイルが見つかりません")
        data = zf.read(sorted(names)[0])
    return _parse_any_xbrl(data)

# ===== コンテキスト抽出・優先順位 =====
def _contexts(tree: etree._ElementTree) -> Dict[str, dict]:
    ctx = {}
    for c in tree.findall(".//xbrli:context", namespaces=NS):
        cid = c.attrib.get("id") or ""
        period = c.find(".//xbrli:period", namespaces=NS)
        if not period:
            continue
        ent = c.find(".//xbrli:entity", namespaces=NS)
        seg = ent.find(".//xbrli:segment", namespaces=NS) if ent is not None else None
        seg_xml = etree.tostring(seg, encoding="unicode") if seg is not None else ""
        consolidated = ("ConsolidatedMember" in seg_xml) or ("連結" in seg_xml) or ("Consolidated" in seg_xml)
        non_consolidated = ("NonConsolidatedMember" in seg_xml) or ("個別" in seg_xml)
        ctx[cid] = {
            "instant": period.findtext("xbrli:instant", namespaces=NS),
            "start": period.findtext("xbrli:startDate", namespaces=NS),
            "end": period.findtext("xbrli:endDate", namespaces=NS),
            "consolidated": consolidated and not non_consolidated,
        }
    return ctx

def _pick_best_context_ids(ctxs: Dict[str, dict]) -> List[str]:
    def score(item: Tuple[str, dict]) -> Tuple[int, int, str]:
        cid, c = item
        duration = 1 if (c.get("start") and c.get("end")) else 0
        cons = 1 if c.get("consolidated") else 0
        end = c.get("end") or c.get("instant") or ""
        return (cons, duration, end)  # 降順
    return [cid for cid,_ in sorted(ctxs.items(), key=score, reverse=True)]

# ===== fact列挙（XBRL / iXBRL） =====
def _iter_facts(tree: etree._ElementTree) -> Iterable[Tuple[str, str, dict]]:
    root = tree.getroot()
    root_local = etree.QName(root).localname.lower()
    if root_local in ("html","xhtml"):
        # iXBRL
        for node in root.findall(".//ix:nonFraction", namespaces=NS) + root.findall(".//ix:nonNumeric", namespaces=NS):
            name = node.attrib.get("name") or ""
            text = "".join(node.itertext()).strip()
            yield (name, text, dict(node.attrib))
        return
    # 通常XBRL
    for el in root.iter():
        qn = etree.QName(el.tag)
        if qn.namespace == NS["xbrli"]:
            continue
        if qn.localname in ("schemaRef",):
            continue
        t = (el.text or "").strip()
        if not t:
            continue
        name = f"{qn.namespace and qn.namespace.split('/')[-1]}:{qn.localname}" if qn.namespace else qn.localname
        yield (name, t, dict(el.attrib))

@dataclass
class XVal:
    value: Optional[float]
    is_percent: bool = False
    unit_ref: Optional[str] = None
    scale: Optional[int] = None

def _xval_from_fact(text: str, attrs: dict, unit_hint: str) -> XVal:
    v = _to_float(text)
    is_pct = _is_percent(text) or _is_percent(attrs.get("unitRef") or "") or _is_percent(unit_hint)
    scale = None
    if attrs.get("scale"):
        try:
            scale = int(attrs["scale"])
        except Exception:
            scale = None
    if v is not None and scale:
        v *= (10 ** scale)
    if v is not None and is_pct:
        v = v / 100.0
    return XVal(value=v, is_percent=is_pct, unit_ref=attrs.get("unitRef"), scale=scale)

def _canon_from_label_or_tag(label_or_tag: str) -> Optional[str]:
    nk = _norm_key(label_or_tag)
    for k, alts in CANON.items():
        if any(_norm_key(a) in nk or nk in _norm_key(a) for a in alts):
            return k
    return TAG2CANON.get(label_or_tag)

# ===== 公開関数：PL/BS/CF抽出 =====
def parse_financials_from_xbrl_bytes(z_or_x_bytes: bytes) -> Dict[str, Dict[str, float]]:
    # zip or raw
    if zipfile.is_zipfile(io.BytesIO(z_or_x_bytes)):
        tree = _load_xbrl_from_zip(z_or_x_bytes)
        unit_hint = "zip"
    else:
        tree = _parse_any_xbrl(z_or_x_bytes)
        unit_hint = "raw"

    ctxs = _contexts(tree)
    order = _pick_best_context_ids(ctxs)

    picked: Dict[str, Tuple[float, int]] = {}  # canon -> (value, rank)
    for tag_or_name, text, attrs in _iter_facts(tree):
        canon = _canon_from_label_or_tag(tag_or_name) or _canon_from_label_or_tag(text)
        if not canon:
            continue
        ctx_id = attrs.get("contextRef")
        rank = order.index(ctx_id) if ctx_id in order else len(order) + 1
        xval = _xval_from_fact(text, attrs, unit_hint)
        if xval.value is None:
            continue
        mult = _infer_unit_multiplier((attrs.get("unitRef") or "") + " " + tag_or_name + " " + text)
        val = float(xval.value) * mult
        # より良い rank（小さい方）を採用
        if (canon not in picked) or (rank < picked[canon][1]):
            picked[canon] = (val, rank)

    sections = {"PL": {}, "BS": {}, "CF": {}}
    label = {
        "revenue": "売上高",
        "operating_income": "営業利益",
        "net_income": "当期純利益",
        "total_assets": "総資産",
        "net_assets": "純資産",
        "equity_ratio_pct": "自己資本比率(%)",
        "cfo": "営業CF",
        "cfi": "投資CF",
        "cff": "財務CF",
    }
    for canon, (v, _) in picked.items():
        sec = CANON2SECTION.get(canon, "PL")
        sections[sec][label.get(canon, canon)] = v
    return sections

def parse_edinet_zip_file(path_or_bytes: Union[str, bytes]) -> Dict[str, Dict[str, float]]:
    if isinstance(path_or_bytes, (bytes, bytearray)):
        return parse_financials_from_xbrl_bytes(path_or_bytes)
    with open(path_or_bytes, "rb") as f:
        return parse_financials_from_xbrl_bytes(f.read())
