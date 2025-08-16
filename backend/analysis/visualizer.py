from io import BytesIO
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import re

# Prefer Japanese-capable fonts but keep graceful fallback
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = [
    "Noto Sans CJK JP",
    "Hiragino Sans",
    "IPAexGothic",
    "Yu Gothic",
    "Yu Gothic UI",
    "Meiryo",
    "DejaVu Sans",
]


def _natural_key(s: str):
    """Split digits and non-digits for natural sorting like 2023, 2023-Q4, etc."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]


def line_chart_image(
    series_map: dict[str, list[tuple[str, float | None]]],
    title: str = "",
    ylabel: str = "",
    yformat: str | None = None,  # 'percent' (expects 0..1), 'percent100' (expects 0..100), 'thousands'
    rotate_xticks: int | None = None,
) -> bytes:
    """
    Render a multi-series line chart to PNG bytes.

    Args:
        series_map: {label: [(x, y), ...]} — None y-values are skipped safely.
        title: chart title.
        ylabel: Y axis label.
        yformat: Optional formatter.
            - 'percent': treat data as 0..1 and show %
            - 'percent100': treat data as already 0..100 and show %
            - 'thousands': show thousands separators
        rotate_xticks: rotate degree for x tick labels (e.g., 30, 45). If None, auto.
    """
    fig = plt.figure(figsize=(7.5, 4.5), dpi=160)
    ax = fig.add_subplot(111)

    # Collect all x labels to unify order across series
    all_x = set()
    cleaned = {}
    for label, points in series_map.items():
        pts = [(str(x), y) for (x, y) in points if y is not None]
        cleaned[label] = pts
        for x, _ in pts:
            all_x.add(str(x))
    ordered_x = sorted(all_x, key=_natural_key) if all_x else []

    # Plot each series aligned to ordered_x where possible
    for label, pts in cleaned.items():
        if not pts:
            continue
        x_to_y = {x: y for x, y in pts}
        xs = ordered_x if ordered_x else [x for x, _ in pts]
        ys = [x_to_y.get(x) for x in xs]
        # Filter out any missing points after alignment while preserving order
        xs_plot, ys_plot = zip(*[(x, y) for x, y in zip(xs, ys) if y is not None]) if any(y is not None for y in ys) else ([], [])
        if xs_plot:
            ax.plot(xs_plot, ys_plot, marker="o", linewidth=2, label=label)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", alpha=0.3)

    # Y-axis formatter
    if yformat == "percent":
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
    elif yformat == "percent100":
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda y, _: f"{y:.1f}%"))
    elif yformat == "thousands":
        ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda y, _: f"{y:,.0f}"))

    # X ticks rotation
    if rotate_xticks is not None:
        for tick in ax.get_xticklabels():
            tick.set_rotation(rotate_xticks)
            tick.set_horizontalalignment("right")
    else:
        # Auto-rotate if too crowded
        if len(ax.get_xticklabels()) > 10:
            for tick in ax.get_xticklabels():
                tick.set_rotation(45)
                tick.set_horizontalalignment("right")

    ax.legend(loc="best")
    ax.margins(x=0.02, y=0.1)
    fig.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
