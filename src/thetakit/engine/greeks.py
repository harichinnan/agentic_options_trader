"""Per-position and portfolio-level greek aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from thetakit.data.adapter import OptionQuote
from thetakit.engine.position import Position
from thetakit.pricing.bsm import GreeksResult, bsm_greeks, time_to_expiry_years


@dataclass(frozen=True, slots=True)
class PositionGreeks:
    position_id: str
    delta: float
    gamma: float
    theta: float
    vega: float
    mark_price: float


@dataclass(frozen=True, slots=True)
class PortfolioGreeks:
    delta: float
    gamma: float
    theta: float
    vega: float
    position_count: int
    mark_value: float


def price_leg(
    leg_strike: float,
    leg_type: str,
    leg_signed_qty: int,
    multiplier: int,
    spot: float,
    expiration: str,
    on: date,
    r: float,
    sigma: float,
) -> GreeksResult:
    """Black-Scholes greeks for a single leg at an observation date."""
    t = time_to_expiry_years(expiration, on.isoformat())
    sigma_safe = max(sigma, 1e-6)
    g = bsm_greeks(
        s=spot, k=leg_strike, t=t, r=r, sigma=sigma_safe, option_type=leg_type  # type: ignore[arg-type]
    )
    return g


def compute_position_greeks(
    position: Position,
    spot: float,
    on: date,
    r: float,
    sigma_by_ticker: dict[str, float] | None = None,
    default_sigma: float = 0.20,
) -> PositionGreeks:
    """Aggregate signed greeks across all legs of a position."""
    total_delta = 0.0
    total_gamma = 0.0
    total_theta = 0.0
    total_vega = 0.0
    mark = 0.0

    for leg in position.legs:
        sigma = (sigma_by_ticker or {}).get(
            f"{leg.symbol}-{leg.option_type}-{leg.strike}-{leg.expiration}",
            default_sigma,
        )
        g = price_leg(
            leg_strike=leg.strike,
            leg_type=leg.option_type,
            leg_signed_qty=leg.signed_quantity,
            multiplier=leg.multiplier,
            spot=spot,
            expiration=leg.expiration,
            on=on,
            r=r,
            sigma=sigma,
        )
        qty = leg.signed_quantity * leg.multiplier
        total_delta += g.delta * qty
        total_gamma += g.gamma * qty
        total_theta += g.theta * qty
        total_vega += g.vega * qty
        mark += g.price * qty

    return PositionGreeks(
        position_id=position.id,
        delta=total_delta,
        gamma=total_gamma,
        theta=total_theta,
        vega=total_vega,
        mark_price=mark,
    )


def aggregate_portfolio(greeks: list[PositionGreeks]) -> PortfolioGreeks:
    return PortfolioGreeks(
        delta=sum(g.delta for g in greeks),
        gamma=sum(g.gamma for g in greeks),
        theta=sum(g.theta for g in greeks),
        vega=sum(g.vega for g in greeks),
        position_count=len(greeks),
        mark_value=sum(g.mark_price for g in greeks),
    )


def lookup_quote(
    chain: list[OptionQuote],
    *,
    strike: float,
    expiration: str,
    option_type: str,
) -> OptionQuote | None:
    """Find a quote matching strike/expiration/type in a chain, with small strike tolerance."""
    best: OptionQuote | None = None
    best_diff = float("inf")
    for q in chain:
        if q.option_type != option_type or q.expiration != expiration:
            continue
        diff = abs(q.strike - strike)
        if diff < best_diff and diff < 0.01:
            best_diff = diff
            best = q
    return best
