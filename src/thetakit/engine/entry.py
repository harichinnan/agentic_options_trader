"""Entry candidate selection.

Given a Strategy and a market snapshot (underlying + option chain), pick
the best-matching option(s) per the delta/DTE targets and return a list
of legs the portfolio can open.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from thetakit.data.adapter import OptionQuote, UnderlyingBar
from thetakit.dsl.schema import EntryRule, StrategyType
from thetakit.engine.position import OptionLeg
from thetakit.pricing.bsm import bsm_greeks, time_to_expiry_years


@dataclass(frozen=True, slots=True)
class EntryCandidate:
    symbol: str
    strategy: StrategyType
    legs: list[OptionLeg]
    expected_credit: float
    short_delta: float
    dte: int


def _signed_delta(quote: OptionQuote, spot: float, r: float, on: date, sigma: float) -> float:
    t = time_to_expiry_years(quote.expiration, on.isoformat())
    if t <= 0:
        return 0.0
    g = bsm_greeks(
        s=spot,
        k=quote.strike,
        t=t,
        r=r,
        sigma=max(quote.implied_volatility or sigma, 1e-6),
        option_type=quote.option_type,  # type: ignore[arg-type]
    )
    return g.delta


def _dte(quote: OptionQuote, on: date) -> int:
    return (date.fromisoformat(quote.expiration) - on).days


def find_entry(
    entry: EntryRule,
    *,
    symbol: str,
    underlying: UnderlyingBar,
    chain: list[OptionQuote],
    on: date,
    r: float = 0.04,
    default_sigma: float = 0.20,
) -> EntryCandidate | None:
    """Select the best contract (or combo) matching the entry rule.

    Returns None when no contract meets the filters (e.g., delta/DTE targets
    cannot be matched within tolerance).
    """
    spot = underlying.close

    # Filter by DTE band
    chain_in_dte = [q for q in chain if abs(_dte(q, on) - entry.dte_target) <= entry.dte_tolerance]
    if not chain_in_dte:
        return None

    if entry.strategy is StrategyType.CSP:
        return _pick_single_short(entry, chain_in_dte, "put", symbol, spot, on, r, default_sigma)
    if entry.strategy is StrategyType.CC:
        return _pick_single_short(entry, chain_in_dte, "call", symbol, spot, on, r, default_sigma)
    if entry.strategy is StrategyType.BULL_PUT_SPREAD:
        return _pick_vertical(
            entry, chain_in_dte, "put", symbol, spot, on, r, default_sigma, bullish=True
        )
    if entry.strategy is StrategyType.BEAR_CALL_SPREAD:
        return _pick_vertical(
            entry, chain_in_dte, "call", symbol, spot, on, r, default_sigma, bullish=False
        )
    if entry.strategy is StrategyType.IRON_CONDOR:
        return _pick_iron_condor(entry, chain_in_dte, symbol, spot, on, r, default_sigma)
    return None


def _pick_single_short(
    entry: EntryRule,
    chain: list[OptionQuote],
    option_type: str,
    symbol: str,
    spot: float,
    on: date,
    r: float,
    sigma: float,
) -> EntryCandidate | None:
    candidates = [q for q in chain if q.option_type == option_type]
    if not candidates:
        return None

    best = None
    best_diff = float("inf")
    best_delta = 0.0
    for q in candidates:
        d = abs(_signed_delta(q, spot, r, on, sigma))
        diff = abs(d - entry.delta_target)
        if diff <= entry.delta_tolerance and diff < best_diff:
            best_diff = diff
            best = q
            best_delta = d

    if best is None:
        return None

    leg = OptionLeg(
        symbol=symbol,
        option_type=option_type,  # type: ignore[arg-type]
        strike=best.strike,
        expiration=best.expiration,
        side="short",
        quantity=1,
    )
    return EntryCandidate(
        symbol=symbol,
        strategy=entry.strategy,
        legs=[leg],
        expected_credit=best.mid * leg.multiplier,
        short_delta=best_delta,
        dte=_dte(best, on),
    )


def _pick_vertical(
    entry: EntryRule,
    chain: list[OptionQuote],
    option_type: str,
    symbol: str,
    spot: float,
    on: date,
    r: float,
    sigma: float,
    *,
    bullish: bool,
) -> EntryCandidate | None:
    short = _pick_single_short(entry, chain, option_type, symbol, spot, on, r, sigma)
    if short is None:
        return None
    wing = entry.wing_width or 5.0
    short_leg = short.legs[0]
    long_strike = short_leg.strike - wing if option_type == "put" else short_leg.strike + wing

    long_q = next(
        (
            q
            for q in chain
            if q.option_type == option_type
            and q.expiration == short_leg.expiration
            and abs(q.strike - long_strike) < 1e-6
        ),
        None,
    )
    if long_q is None:
        return None

    long_leg = OptionLeg(
        symbol=symbol,
        option_type=option_type,  # type: ignore[arg-type]
        strike=long_q.strike,
        expiration=long_q.expiration,
        side="long",
        quantity=1,
    )
    # Credit = short premium - long premium
    short_q = next(
        q
        for q in chain
        if q.option_type == option_type
        and q.strike == short_leg.strike
        and q.expiration == short_leg.expiration
    )
    credit_per = max(short_q.mid - long_q.mid, 0.01)

    return EntryCandidate(
        symbol=symbol,
        strategy=entry.strategy,
        legs=[short_leg, long_leg],
        expected_credit=credit_per * short_leg.multiplier,
        short_delta=short.short_delta,
        dte=short.dte,
    )


def _pick_iron_condor(
    entry: EntryRule,
    chain: list[OptionQuote],
    symbol: str,
    spot: float,
    on: date,
    r: float,
    sigma: float,
) -> EntryCandidate | None:
    put_side = _pick_vertical(entry, chain, "put", symbol, spot, on, r, sigma, bullish=True)
    call_side = _pick_vertical(entry, chain, "call", symbol, spot, on, r, sigma, bullish=False)
    if put_side is None or call_side is None:
        return None
    legs = put_side.legs + call_side.legs
    credit = put_side.expected_credit + call_side.expected_credit
    return EntryCandidate(
        symbol=symbol,
        strategy=entry.strategy,
        legs=legs,
        expected_credit=credit,
        short_delta=max(put_side.short_delta, call_side.short_delta),
        dte=put_side.dte,
    )
