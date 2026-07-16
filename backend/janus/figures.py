"""
Publication figures from a project's real analysis results (docs/JANUS.md v5).

Turns the stored analysis runs into crisp, paper-ready figures instead of just
tile URLs: a results chart of every headline metric, a study-area map (the AOI
geometry drawn to scale with a global locator), and a ground-truth validation
chart. Everything is emitted as standalone SVG — vector, so it stays sharp at
any size, imports cleanly into Google Docs and HTML, and drops into LaTeX /
Overleaf via `\\usepackage{svg}` + `\\includesvg`. Pure string building, no
plotting dependency, so it behaves identically in local dev and on Cloud Run.

Every figure is drawn only from stored tool events, so a figure can never show
a run that did not happen. Figures use a white background and the Kairos accent
palette (teal for data, amber for the study area) so they sit correctly on a
printed page rather than the dark app.
"""

from __future__ import annotations

import html
import math
import re
from datetime import date

from janus import store

# Kairos palette, tuned for a white page rather than the dark app.
INK = "#0B120E"
DIM = "#5B6B5D"
GRID = "#D7DED8"
TEAL = "#00BFA8"
TEAL_DK = "#049482"
AMBER = "#E8A318"
PAPER = "#FFFFFF"

FONT = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', "
    "Arial, sans-serif"
)

FIGURE_KINDS = ("results", "study_area", "validation")


# --------------------------------------------------------------------------- #
# Data collection — numeric, straight from stored runs.
# --------------------------------------------------------------------------- #
def _num(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def collect_runs(project_id: int) -> list[dict]:
    """Every run_analysis event, with numeric headline value + uncertainty."""
    runs = []
    for msg in store.get_messages(project_id):
        for ev in msg.get("tool_events") or []:
            if ev.get("tool") != "run_analysis" or not ev.get("result"):
                continue
            r = ev["result"]
            hs = r.get("headline_stat") or {}
            runs.append(
                {
                    "analysis_type": r.get("analysis_type"),
                    "display_name": r.get("display_name") or r.get("analysis_type"),
                    "bbox": r.get("bbox"),
                    "label": hs.get("label") or "Result",
                    "value": _num(hs.get("value")),
                    "unit": hs.get("unit") or "",
                    "low": _num(r.get("flood_area_low_km2")),
                    "high": _num(r.get("flood_area_high_km2")),
                    "confidence": _num(r.get("confidence")),
                    "data_date": r.get("data_date"),
                }
            )
    return runs


def collect_validations(project_id: int) -> list[dict]:
    vals = []
    for msg in store.get_messages(project_id):
        for ev in msg.get("tool_events") or []:
            if ev.get("tool") != "run_ground_truth_validation" or not ev.get(
                "validation"
            ):
                continue
            v = ev["validation"]
            m = v.get("metrics") or {}
            vals.append(
                {
                    "region": (v.get("benchmark") or {}).get("region") or "Benchmark",
                    "iou": _num(m.get("iou")),
                    "precision": _num(m.get("precision")),
                    "recall": _num(m.get("recall")),
                    "f1": _num(m.get("f1")),
                }
            )
    return vals


def available_figures(project_id: int) -> list[str]:
    """Which figure kinds have data to render for this project."""
    kinds = []
    runs = collect_runs(project_id)
    if any(r["value"] is not None for r in runs):
        kinds.append("results")
    if any(r["bbox"] for r in runs) or (store.get_project(project_id).get("design") or {}).get("bbox"):
        kinds.append("study_area")
    if collect_validations(project_id):
        kinds.append("validation")
    return kinds


# --------------------------------------------------------------------------- #
# SVG helpers.
# --------------------------------------------------------------------------- #
def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _svg_open(w: int, h: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="{FONT}" '
        f'role="img" aria-label="{_esc(title)}">',
        f'<rect width="{w}" height="{h}" fill="{PAPER}"/>',
    ]


def _text(x, y, s, size=13, fill=INK, weight="normal", anchor="start", rotate=None):
    tr = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}" text-anchor="{anchor}"{tr}>{_esc(s)}</text>'
    )


def _nice_ticks(max_value: float, count: int = 5) -> list[float]:
    """A small set (~count) of round-number gridline values covering 0..max."""
    if max_value <= 0:
        return [0, 1]
    rough = max_value / count
    mag = 10 ** math.floor(math.log10(rough))
    step = mag * 10
    for m in (1, 2, 2.5, 5, 10):
        if m * mag * count >= max_value:
            step = m * mag
            break
    n = int(math.ceil(max_value / step))
    return [round(i * step, 6) for i in range(n + 1)]


def _fmt(v: float) -> str:
    if v == int(v):
        return str(int(v))
    if abs(v) >= 100:
        return f"{v:.0f}"
    if abs(v) >= 1:
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return f"{v:.3f}".rstrip("0").rstrip(".")


# --------------------------------------------------------------------------- #
# Results figure — horizontal bars of every headline metric.
# --------------------------------------------------------------------------- #
def results_figure_svg(project_id: int) -> str:
    project = store.get_project(project_id)
    runs = [r for r in collect_runs(project_id) if r["value"] is not None]
    W = 900
    pad_l, pad_r, pad_t = 260, 60, 96
    row_h, gap = 46, 20
    H = pad_t + max(1, len(runs)) * (row_h + gap) + 70

    out = _svg_open(W, H, "Analysis results")
    out.append(_text(48, 46, project.get("title", "Results"), 20, INK, "700"))
    out.append(
        _text(
            48,
            70,
            "Headline analysis results — Kairos + Janus",
            13,
            DIM,
        )
    )

    if not runs:
        out.append(_text(48, pad_t + 30, "No numeric results yet.", 14, DIM))
        out.append("</svg>")
        return "\n".join(out)

    # Different analyses report different units (km², t/ha, ppb…). Putting them
    # on one shared axis would be dishonest, so bars are scaled WITHIN each unit
    # and a shared axis with tick numbers is only drawn when every run shares a
    # single unit (then the comparison is real).
    units = [r["unit"] for r in runs]
    single_unit = len(set(units)) == 1
    unit_max = {}
    for r in runs:
        unit_max[r["unit"]] = max(unit_max.get(r["unit"], 0.0), r["value"], r["high"] or 0)
    for u in unit_max:
        unit_max[u] = unit_max[u] or 1.0

    # Leave the right third for the value + confidence labels.
    plot_w = (W - pad_l - pad_r) * 0.72
    bottom = pad_t + len(runs) * (row_h + gap)

    def frac(r, v):
        return v / unit_max[r["unit"]]

    if single_unit:
        axis_max = _nice_ticks(unit_max[units[0]])[-1]
        axis_max = max(axis_max, unit_max[units[0]])
        for u in unit_max:
            unit_max[u] = axis_max
        for t in _nice_ticks(axis_max):
            x = pad_l + (t / axis_max) * plot_w
            out.append(
                f'<line x1="{x:.1f}" y1="{pad_t - 10}" x2="{x:.1f}" y2="{bottom}" '
                f'stroke="{GRID}" stroke-width="1"/>'
            )
            out.append(_text(x, bottom + 22, _fmt(t), 12, DIM, anchor="middle"))
        out.append(
            _text(pad_l + plot_w / 2, H - 18, units[0], 12, DIM, anchor="middle")
        )
    else:
        out.append(
            _text(
                pad_l,
                H - 18,
                "Bars scaled within each metric — compare the printed values, "
                "not bar lengths, across rows.",
                11,
                DIM,
            )
        )

    for i, r in enumerate(runs):
        y = pad_t + i * (row_h + gap)
        cy = y + row_h / 2
        name = r["display_name"]
        if len(name) > 30:
            name = name[:29] + "…"
        out.append(_text(pad_l - 16, cy - 2, name, 14, INK, "600", "end"))
        out.append(_text(pad_l - 16, cy + 15, r["label"], 11, DIM, anchor="end"))
        # Bar.
        bar_end = pad_l + frac(r, r["value"]) * plot_w
        out.append(
            f'<rect x="{pad_l}" y="{y + 8}" width="{max(bar_end - pad_l, 1):.1f}" '
            f'height="{row_h - 16}" rx="4" fill="{TEAL}"/>'
        )
        # Uncertainty whisker (same unit scale).
        right_edge = bar_end
        if r["low"] is not None and r["high"] is not None and r["high"] > r["low"]:
            x1 = pad_l + frac(r, r["low"]) * plot_w
            x2 = pad_l + frac(r, r["high"]) * plot_w
            right_edge = max(right_edge, x2)
            wy = y + row_h / 2
            out.append(
                f'<line x1="{x1:.1f}" y1="{wy}" x2="{x2:.1f}" y2="{wy}" '
                f'stroke="{TEAL_DK}" stroke-width="2"/>'
            )
            for xx in (x1, x2):
                out.append(
                    f'<line x1="{xx:.1f}" y1="{wy - 6}" x2="{xx:.1f}" '
                    f'y2="{wy + 6}" stroke="{TEAL_DK}" stroke-width="2"/>'
                )
        # Value + confidence, always clear of the bar and whisker.
        vx = right_edge + 12
        out.append(
            _text(vx, cy + 5, f'{_fmt(r["value"])} {r["unit"]}'.strip(), 13, INK, "700")
        )
        if r["confidence"] is not None:
            conf = (
                f'confidence {int(round(r["confidence"] * 100))}%'
                if r["confidence"] <= 1
                else f'confidence {_fmt(r["confidence"])}'
            )
            out.append(_text(vx, cy + 21, conf, 10, DIM))

    out.append(
        f'<line x1="{pad_l}" y1="{pad_t - 10}" x2="{pad_l}" y2="{bottom}" '
        f'stroke="{INK}" stroke-width="1.5"/>'
    )
    out.append("</svg>")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Study-area figure — the AOI bbox drawn to scale + a global locator.
# --------------------------------------------------------------------------- #
def _project_bbox(project_id: int) -> list | None:
    design = store.get_project(project_id).get("design") or {}
    if design.get("bbox"):
        return design["bbox"]
    for r in collect_runs(project_id):
        if r["bbox"]:
            return r["bbox"]
    return None


def study_area_figure_svg(project_id: int) -> str:
    project = store.get_project(project_id)
    bbox = _project_bbox(project_id)
    W, H = 900, 520
    out = _svg_open(W, H, "Study area")
    out.append(_text(48, 46, "Study area", 20, INK, "700"))
    out.append(
        _text(48, 70, project.get("title", ""), 13, DIM)
    )
    if not bbox or len(bbox) != 4:
        out.append(_text(48, 120, "No study area defined yet.", 14, DIM))
        out.append("</svg>")
        return "\n".join(out)

    min_lon, min_lat, max_lon, max_lat = [float(v) for v in bbox]
    c_lon, c_lat = (min_lon + max_lon) / 2, (min_lat + max_lat) / 2

    # --- Main panel: AOI rectangle to scale with lon/lat ticks. ---
    px, py, pw, ph = 48, 100, 520, 360
    out.append(
        f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="#F5F8F5" '
        f'stroke="{GRID}" stroke-width="1"/>'
    )
    span_lon = max(max_lon - min_lon, 1e-4)
    span_lat = max(max_lat - min_lat, 1e-4)
    # Pad the view so the AOI sits in a margin of context.
    view_lon = span_lon * 1.6
    view_lat = span_lat * 1.6
    # Keep aspect ratio square-ish by matching the larger span.
    view = max(view_lon, view_lat)
    vlon0, vlon1 = c_lon - view / 2, c_lon + view / 2
    vlat0, vlat1 = c_lat - view / 2, c_lat + view / 2
    sx = lambda lon: px + (lon - vlon0) / (vlon1 - vlon0) * pw
    sy = lambda lat: py + (vlat1 - lat) / (vlat1 - vlat0) * ph

    # graticule
    for k in range(5):
        gx = px + k * pw / 4
        gy = py + k * ph / 4
        out.append(
            f'<line x1="{gx:.1f}" y1="{py}" x2="{gx:.1f}" y2="{py + ph}" '
            f'stroke="{GRID}" stroke-width="0.75"/>'
        )
        out.append(
            f'<line x1="{px}" y1="{gy:.1f}" x2="{px + pw}" y2="{gy:.1f}" '
            f'stroke="{GRID}" stroke-width="0.75"/>'
        )
        lon_v = vlon0 + k * (vlon1 - vlon0) / 4
        lat_v = vlat1 - k * (vlat1 - vlat0) / 4
        out.append(_text(gx, py + ph + 18, f"{lon_v:.2f}°", 10, DIM, anchor="middle"))
        out.append(_text(px - 8, gy + 4, f"{lat_v:.2f}°", 10, DIM, anchor="end"))

    # AOI rectangle
    rx, ry = sx(min_lon), sy(max_lat)
    rw, rh = sx(max_lon) - sx(min_lon), sy(min_lat) - sy(max_lat)
    out.append(
        f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
        f'fill="{AMBER}" fill-opacity="0.18" stroke="{AMBER}" stroke-width="2"/>'
    )
    out.append(
        f'<circle cx="{sx(c_lon):.1f}" cy="{sy(c_lat):.1f}" r="3" fill="{AMBER}"/>'
    )

    # scale bar (approx km, longitude at centre latitude)
    import math

    km_per_deg_lon = 111.32 * math.cos(math.radians(c_lat))
    width_km = span_lon * km_per_deg_lon
    height_km = span_lat * 110.57
    # pick a round scale-bar length ~ 1/3 of the view width in km
    view_km = view * km_per_deg_lon
    target = view_km / 3
    nice = 1
    for n in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000):
        if n >= target:
            nice = n
            break
    bar_px = nice / view_km * pw if view_km else 0
    bx, by = px + 14, py + ph - 20
    out.append(
        f'<line x1="{bx}" y1="{by}" x2="{bx + bar_px:.1f}" y2="{by}" '
        f'stroke="{INK}" stroke-width="3"/>'
    )
    out.append(_text(bx, by - 8, f"{nice} km", 11, INK, "600"))

    # --- Side facts + global locator. ---
    fx = 600
    out.append(_text(fx, py + 8, "COORDINATES", 11, DIM, "700"))
    facts = [
        f"Centre  {c_lat:.3f}°, {c_lon:.3f}°",
        f"Lon  {min_lon:.3f}° → {max_lon:.3f}°",
        f"Lat  {min_lat:.3f}° → {max_lat:.3f}°",
        f"Extent  {width_km:.0f} × {height_km:.0f} km",
        f"Area  ~{width_km * height_km:,.0f} km²",
    ]
    for i, f in enumerate(facts):
        out.append(_text(fx, py + 34 + i * 22, f, 13, INK))

    # global locator: equirectangular graticule + AOI marker
    gx0, gy0, gw, gh = fx, py + 170, 252, 126
    out.append(
        f'<rect x="{gx0}" y="{gy0}" width="{gw}" height="{gh}" fill="#EEF3EE" '
        f'stroke="{GRID}" stroke-width="1"/>'
    )
    for lon in range(-180, 181, 60):
        gx = gx0 + (lon + 180) / 360 * gw
        out.append(
            f'<line x1="{gx:.1f}" y1="{gy0}" x2="{gx:.1f}" y2="{gy0 + gh}" '
            f'stroke="{GRID}" stroke-width="0.5"/>'
        )
    for lat in range(-90, 91, 45):
        gy = gy0 + (90 - lat) / 180 * gh
        out.append(
            f'<line x1="{gx0}" y1="{gy:.1f}" x2="{gx0 + gw}" y2="{gy:.1f}" '
            f'stroke="{GRID}" stroke-width="0.5"/>'
        )
    # equator emphasised
    eq = gy0 + gh / 2
    out.append(
        f'<line x1="{gx0}" y1="{eq:.1f}" x2="{gx0 + gw}" y2="{eq:.1f}" '
        f'stroke="{DIM}" stroke-width="0.75"/>'
    )
    mx = gx0 + (c_lon + 180) / 360 * gw
    my = gy0 + (90 - c_lat) / 180 * gh
    out.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="5" fill="{AMBER}" '
               f'stroke="{PAPER}" stroke-width="1.5"/>')
    out.append(_text(gx0, gy0 + gh + 18, "Global location", 10, DIM))

    out.append("</svg>")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Validation figure — IoU / precision / recall / F1 per benchmark.
# --------------------------------------------------------------------------- #
def validation_figure_svg(project_id: int) -> str:
    vals = collect_validations(project_id)
    W = 900
    pad_l, pad_t = 70, 96
    group_w = 220
    H = 460
    out = _svg_open(W, H, "Ground-truth validation")
    out.append(_text(48, 46, "Ground-truth validation", 20, INK, "700"))
    out.append(
        _text(48, 70, "Skill against independent benchmark events", 13, DIM)
    )
    if not vals:
        out.append(_text(48, pad_t + 30, "No validation runs yet.", 14, DIM))
        out.append("</svg>")
        return "\n".join(out)

    metrics = [("IoU", "iou"), ("Precision", "precision"), ("Recall", "recall"), ("F1", "f1")]
    colors = [TEAL, TEAL_DK, AMBER, "#9BA7F5"]
    plot_h = 260
    base = pad_t + plot_h
    # y grid 0..1
    for g in range(6):
        v = g / 5
        y = base - v * plot_h
        out.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W - 40}" y2="{y:.1f}" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
        out.append(_text(pad_l - 10, y + 4, f"{v:.1f}", 11, DIM, anchor="end"))

    n_groups = len(vals)
    avail = W - pad_l - 60
    step = min(group_w, avail / n_groups)
    bar_w = step / (len(metrics) + 1)
    for gi, v in enumerate(vals):
        gx = pad_l + gi * step + (step - bar_w * len(metrics)) / 2
        for mi, (mlabel, mkey) in enumerate(metrics):
            val = v.get(mkey)
            if val is None:
                continue
            val = max(0.0, min(1.0, val))
            bx = gx + mi * bar_w
            bh = val * plot_h
            out.append(
                f'<rect x="{bx:.1f}" y="{base - bh:.1f}" width="{bar_w - 3:.1f}" '
                f'height="{bh:.1f}" rx="2" fill="{colors[mi]}"/>'
            )
            out.append(
                _text(bx + bar_w / 2 - 1, base - bh - 5, _fmt(val), 9, INK, anchor="middle")
            )
        region = v["region"]
        if len(region) > 22:
            region = region[:21] + "…"
        out.append(
            _text(gx + bar_w * len(metrics) / 2, base + 20, region, 12, INK, "600", "middle")
        )

    # legend
    lx = pad_l
    ly = base + 56
    for mi, (mlabel, _k) in enumerate(metrics):
        out.append(
            f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" rx="2" fill="{colors[mi]}"/>'
        )
        out.append(_text(lx + 18, ly, mlabel, 12, INK))
        lx += 130

    out.append("</svg>")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Dispatch.
# --------------------------------------------------------------------------- #
_BUILDERS = {
    "results": results_figure_svg,
    "study_area": study_area_figure_svg,
    "validation": validation_figure_svg,
}


def build_figure(project_id: int, kind: str) -> str:
    builder = _BUILDERS.get(kind)
    if not builder:
        raise ValueError(f"Unknown figure kind: {kind}")
    return builder(project_id)


def project_slug(project: dict) -> str:
    """Collapse a title to a filename slug — matches the frontend's slugify so a
    LaTeX \\includesvg reference resolves to the SVG the user downloaded."""
    return (
        re.sub(r"[^a-z0-9]+", "-", (project.get("title") or "project").lower())
        .strip("-")[:50]
        or "project"
    )


def figure_filename(project: dict, kind: str) -> str:
    return f"kairos-{kind.replace('_', '-')}-{project_slug(project)}.svg"


def _figures_generated_note() -> str:
    return f"Figures generated {date.today().isoformat()} by Janus."
