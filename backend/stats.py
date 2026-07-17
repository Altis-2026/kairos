"""
Trend statistics for extracted time series — pure Python, no scipy/numpy.

Two complementary tests, because reviewers expect both:

  * OLS linear regression — slope (per year), r², and a two-sided p-value for
    the slope computed from the exact Student-t distribution (regularized
    incomplete beta via continued fractions, Numerical-Recipes style), not a
    normal approximation.
  * Mann-Kendall — the field-standard nonparametric monotonic-trend test
    (robust to outliers and non-normality), with the tie-corrected variance
    and the usual normal approximation for its Z statistic, plus Sen's slope
    (median of pairwise slopes) as the robust rate estimate.

Dates are converted to fractional years so both slopes read "per year".
"""

import math
from datetime import datetime

# ---------------------------------------------------------------------------
# Student-t p-value machinery (exact, via the regularized incomplete beta).
# ---------------------------------------------------------------------------


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function."""
    MAXIT, EPS, FPMIN = 200, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_bt = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    bt = math.exp(ln_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _t_sf_two_sided(t: float, df: float) -> float:
    """Two-sided p-value for a Student-t statistic with df degrees of freedom."""
    if df <= 0:
        return 1.0
    return _betai(df / 2.0, 0.5, df / (df + t * t))


def _norm_sf_two_sided(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def _to_years(dates: list) -> list:
    """ISO date strings -> fractional years since the first observation."""
    ts = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
    t0 = ts[0]
    return [(t - t0).days / 365.25 for t in ts]


# ---------------------------------------------------------------------------
# The public API.
# ---------------------------------------------------------------------------


def ols_trend(dates: list, values: list) -> dict:
    """Least-squares line through (t_years, value); slope in units/year."""
    n = len(values)
    if n < 3:
        raise ValueError("Need at least 3 points for a trend.")
    x = _to_years(dates)
    mean_x = sum(x) / n
    mean_y = sum(values) / n
    sxx = sum((xi - mean_x) ** 2 for xi in x)
    sxy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, values))
    syy = sum((yi - mean_y) ** 2 for yi in values)
    if sxx == 0:
        raise ValueError("All observations share one date; no trend estimable.")

    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    ss_res = sum(
        (yi - (intercept + slope * xi)) ** 2 for xi, yi in zip(x, values)
    )
    r2 = 1.0 - ss_res / syy if syy > 0 else 0.0

    df = n - 2
    if df > 0 and ss_res > 0:
        se = math.sqrt((ss_res / df) / sxx)
        t = slope / se if se > 0 else float("inf")
        p = _t_sf_two_sided(t, df)
    else:
        p = 0.0 if slope != 0 else 1.0

    return {
        "slope_per_year": round(slope, 5),
        "intercept": round(intercept, 4),
        "r_squared": round(max(0.0, min(1.0, r2)), 3),
        "p_value": round(p, 5),
        "n": n,
    }


def mann_kendall(dates: list, values: list) -> dict:
    """Tie-corrected Mann-Kendall test + Sen's slope (units/year)."""
    n = len(values)
    if n < 4:
        raise ValueError("Mann-Kendall needs at least 4 points.")

    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            d = values[j] - values[i]
            s += (d > 0) - (d < 0)

    # Tie-corrected variance.
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    tie_term = sum(t * (t - 1) * (2 * t + 5) for t in counts.values() if t > 1)
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0

    if var_s <= 0:
        z = 0.0
    elif s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0
    p = _norm_sf_two_sided(z)

    # Sen's slope: median of all pairwise slopes over fractional years.
    x = _to_years(dates)
    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            dt = x[j] - x[i]
            if dt != 0:
                slopes.append((values[j] - values[i]) / dt)
    slopes.sort()
    m = len(slopes)
    sen = (
        slopes[m // 2]
        if m % 2 == 1
        else (slopes[m // 2 - 1] + slopes[m // 2]) / 2.0
    ) if m else 0.0

    if p < 0.05:
        trend = "increasing" if s > 0 else "decreasing"
    else:
        trend = "no significant trend"

    return {
        "s": s,
        "z": round(z, 3),
        "p_value": round(p, 5),
        "trend": trend,
        "sen_slope_per_year": round(sen, 5),
        "n": n,
    }


def trend_report(points: list) -> dict:
    """Both tests over [{date, value}...] plus a one-line plain reading."""
    dates = [p["date"] for p in points]
    values = [float(p["value"]) for p in points]
    ols = ols_trend(dates, values)
    mk = mann_kendall(dates, values)

    if mk["p_value"] < 0.05 and ols["p_value"] < 0.05:
        strength = "Both tests agree"
    elif mk["p_value"] < 0.05 or ols["p_value"] < 0.05:
        strength = "Only one test reaches significance — treat with caution"
    else:
        strength = "Neither test finds a significant trend"
    summary = (
        f"{strength}: Mann-Kendall says {mk['trend']} "
        f"(p={mk['p_value']}), Sen's slope {mk['sen_slope_per_year']}/yr; "
        f"OLS slope {ols['slope_per_year']}/yr (r²={ols['r_squared']}, "
        f"p={ols['p_value']})."
    )
    return {"ols": ols, "mann_kendall": mk, "summary": summary}
