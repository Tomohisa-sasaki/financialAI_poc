from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import base64
import datetime
import re

_percent_metric_names = {
    "ROE",
    "ROA",
    "EQUITY_RATIO",
    "NET_MARGIN",
    "OPERATING_MARGIN",
    "GROSS_MARGIN",
    "REVENUE_GROWTH",
}

_period_rx = re.compile(r"(?P<y>\d{4})(?:[-/ ]?Q(?P<q>[1-4]))?")


def _period_key(p: str):
    s = str(p)
    m = _period_rx.search(s)
    if not m:
        return (float("inf"), float("inf"))
    y = int(m.group("y"))
    q = int(m.group("q") or 0)
    return (y, q)


def _fmt_metric(name: str, val):
    if val is None:
        return ""
    try:
        v = float(val)
    except Exception:
        return str(val)

    if name.upper() in _percent_metric_names:
        # Accept both decimals (0.123) and already-in-percent (12.3)
        pct = v * 100.0 if abs(v) <= 1.0 else v
        return f"{pct:.2f}%"
    # thousands separator for large numbers
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.2f}" if abs(v) < 100 else f"{v:.0f}"


def build_pdf(
    title: str,
    companies: list,
    metrics: list[str],
    charts_b64: list[str],
    scenario: dict | None = None,
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    H1 = styles["Heading1"]
    BODY = styles["BodyText"]

    elems = []
    elems.append(Paragraph(f"<b>{title}</b>", H1))
    elems.append(Spacer(1, 12))

    # Determine the latest period across all companies/metrics
    latest_period = None
    for comp in companies:
        for metric, vals in (comp.get("metrics", {}) or {}).items():
            for p in (vals or {}).keys():
                if latest_period is None:
                    latest_period = p
                else:
                    latest_period = max(latest_period, p, key=_period_key)

    if latest_period:
        header = [f"Metric ({latest_period})"] + [c.get("name", "-") for c in companies]
        rows = [header]
        for m in metrics:
            row = [m]
            for c in companies:
                mv = (c.get("metrics", {}) or {}).get(m, {}) or {}
                v = None
                # exact match first
                if str(latest_period) in mv:
                    v = mv[str(latest_period)]
                else:
                    # try best-effort: pick max period available for this metric
                    if mv:
                        best_p = max(mv.keys(), key=_period_key)
                        v = mv[best_p]
                row.append(_fmt_metric(m, v))
            rows.append(row)

        t = Table(rows, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ]
            )
        )
        elems.append(t)
        elems.append(Spacer(1, 12))

    if scenario:
        elems.append(Paragraph("<b>Scenario</b>", BODY))
        elems.append(Paragraph(str(scenario), BODY))
        elems.append(Spacer(1, 12))

    for b64 in charts_b64:
        try:
            payload = b64.split(",", 1)[1] if b64.startswith("data:image") else b64
            img = Image(BytesIO(base64.b64decode(payload)))
            img.drawHeight = 4 * 72
            img.drawWidth = 6 * 72
            elems.append(img)
            elems.append(Spacer(1, 12))
        except Exception:
            # Skip broken image payloads safely
            continue

    foot = f"Data source: EDINET / J-Quants. Generated on {datetime.date.today().isoformat()}."
    elems.append(Paragraph(f"<font size=8>{foot}</font>", BODY))

    doc.title = title
    doc.build(elems)
    return buf.getvalue()
