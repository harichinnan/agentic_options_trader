"""Black-Scholes-Merton pricing and greeks for European options.

Pure numpy/scipy — no external pricing library — so installs are light
and behavior is deterministic. American-exercise deviations are handled
with a simple heuristic in `pricing.american`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.stats import norm

OptionType = Literal["call", "put"]


@dataclass(frozen=True, slots=True)
class GreeksResult:
    """Greeks + price. Theta is per-calendar-day (not per-year)."""

    price: float
    delta: float
    gamma: float
    theta: float  # per day
    vega: float  # per 1-vol-point (0.01 change in sigma)
    rho: float  # per 1% change in r


def _d1_d2(
    s: float, k: float, t: float, r: float, q: float, sigma: float
) -> tuple[float, float]:
    if t <= 0 or sigma <= 0:
        raise ValueError("t and sigma must be positive")
    srt = sigma * math.sqrt(t)
    d1 = (math.log(s / k) + (r - q + 0.5 * sigma * sigma) * t) / srt
    d2 = d1 - srt
    return d1, d2


def bsm_price(
    s: float,
    k: float,
    t: float,
    r: float,
    sigma: float,
    option_type: OptionType = "call",
    q: float = 0.0,
) -> float:
    """Black-Scholes-Merton option price.

    Args:
        s: underlying spot
        k: strike
        t: time to expiration in years (calendar, act/365)
        r: risk-free rate (annualized, continuous)
        sigma: implied volatility (annualized)
        option_type: 'call' or 'put'
        q: continuous dividend yield

    Returns:
        Fair value of the option.
    """
    if t <= 0:
        # Intrinsic at expiry
        if option_type == "call":
            return max(s - k, 0.0)
        return max(k - s, 0.0)
    if sigma <= 0:
        # Sigma=0 -> deterministic forward
        fwd = s * math.exp((r - q) * t)
        disc = math.exp(-r * t)
        if option_type == "call":
            return max(fwd - k, 0.0) * disc
        return max(k - fwd, 0.0) * disc

    d1, d2 = _d1_d2(s, k, t, r, q, sigma)
    if option_type == "call":
        return s * math.exp(-q * t) * norm.cdf(d1) - k * math.exp(-r * t) * norm.cdf(d2)
    return k * math.exp(-r * t) * norm.cdf(-d2) - s * math.exp(-q * t) * norm.cdf(-d1)


def bsm_greeks(
    s: float,
    k: float,
    t: float,
    r: float,
    sigma: float,
    option_type: OptionType = "call",
    q: float = 0.0,
) -> GreeksResult:
    """Full pricing + greeks. Theta scaled to per-calendar-day, vega per 1 vol point."""
    if t <= 0 or sigma <= 0:
        price = bsm_price(s, k, t, max(sigma, 1e-9), option_type, q)
        # At/past expiry: all greeks collapse to indicator-style values
        return GreeksResult(price=price, delta=0.0, gamma=0.0, theta=0.0, vega=0.0, rho=0.0)

    d1, d2 = _d1_d2(s, k, t, r, q, sigma)
    pdf_d1 = float(norm.pdf(d1))
    disc_r = math.exp(-r * t)
    disc_q = math.exp(-q * t)

    price = bsm_price(s, k, t, r, sigma, option_type, q)
    gamma = disc_q * pdf_d1 / (s * sigma * math.sqrt(t))
    vega_per_unit = s * disc_q * pdf_d1 * math.sqrt(t)  # per 1.0 change in sigma
    vega = vega_per_unit * 0.01  # per 1 vol point (e.g., 20->21 vol)

    if option_type == "call":
        delta = disc_q * float(norm.cdf(d1))
        theta_annual = (
            -(s * disc_q * pdf_d1 * sigma) / (2 * math.sqrt(t))
            - r * k * disc_r * float(norm.cdf(d2))
            + q * s * disc_q * float(norm.cdf(d1))
        )
        rho = k * t * disc_r * float(norm.cdf(d2)) * 0.01
    else:
        delta = disc_q * (float(norm.cdf(d1)) - 1.0)
        theta_annual = (
            -(s * disc_q * pdf_d1 * sigma) / (2 * math.sqrt(t))
            + r * k * disc_r * float(norm.cdf(-d2))
            - q * s * disc_q * float(norm.cdf(-d1))
        )
        rho = -k * t * disc_r * float(norm.cdf(-d2)) * 0.01

    theta_per_day = theta_annual / 365.0

    return GreeksResult(
        price=price,
        delta=delta,
        gamma=gamma,
        theta=theta_per_day,
        vega=vega,
        rho=rho,
    )


def implied_volatility(
    market_price: float,
    s: float,
    k: float,
    t: float,
    r: float,
    option_type: OptionType = "call",
    q: float = 0.0,
    *,
    tol: float = 1e-6,
    max_iter: int = 100,
) -> float:
    """Solve for implied volatility via Brent's method in [1e-4, 5.0].

    Returns NaN if no valid solution exists (e.g., market_price < intrinsic).
    """
    if t <= 0 or market_price <= 0:
        return float("nan")

    intrinsic = bsm_price(s, k, t, r, 1e-8, option_type, q)
    if market_price < intrinsic - 1e-6:
        return float("nan")

    lo, hi = 1e-4, 5.0

    def f(sigma: float) -> float:
        return bsm_price(s, k, t, r, sigma, option_type, q) - market_price

    try:
        f_lo = f(lo)
        f_hi = f(hi)
    except ValueError:
        return float("nan")

    if f_lo * f_hi > 0:
        # No sign change in bracket — try expanding once, else bail
        try:
            f_hi2 = f(10.0)
        except ValueError:
            return float("nan")
        if f_lo * f_hi2 > 0:
            return float("nan")
        hi = 10.0
        f_hi = f_hi2

    # Bisection — robust for this problem and avoids scipy.optimize dependency here
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = f(mid)
        if abs(f_mid) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid
        if hi - lo < tol:
            return 0.5 * (lo + hi)
    return 0.5 * (lo + hi)


def time_to_expiry_years(
    expiration_date: str | np.datetime64, as_of_date: str | np.datetime64
) -> float:
    """Calendar days / 365 between two ISO dates or numpy datetime64."""
    exp = np.datetime64(str(expiration_date)[:10])
    asof = np.datetime64(str(as_of_date)[:10])
    days = (exp - asof).astype("timedelta64[D]").astype(int)
    return max(days, 0) / 365.0
