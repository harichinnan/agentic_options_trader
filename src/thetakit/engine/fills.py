"""Slippage / fill modeling.

Default model (per spec 7.4):
- Fill at mid ± (spread_pct * bid_ask_spread / 2) where spread_pct defaults to 0.4
- When a roll is triggered by an intraday test, the penalty is increased by
  10% of the slippage.

In synthetic-data mode, bid/ask are derived from a fixed % of the mid price
unless the data adapter supplies them directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FillDirection = Literal["sell_to_open", "buy_to_close", "buy_to_open", "sell_to_close"]


@dataclass(frozen=True, slots=True)
class FillModel:
    spread_pct: float = 0.4  # Fraction of bid/ask spread crossed
    intraday_roll_penalty: float = 1.1  # Multiplier on spread crossing when tested
    synthetic_spread_pct: float = 0.05  # Used when adapter has no bid/ask

    def effective_fill(
        self,
        *,
        mid: float,
        direction: FillDirection,
        bid: float | None = None,
        ask: float | None = None,
        roll_tested: bool = False,
    ) -> float:
        """Return the fill price given a mid and (optional) bid/ask.

        Conventions:
        - sell_*  → you receive less (fill below mid)
        - buy_*   → you pay more (fill above mid)
        """
        if bid is None or ask is None or ask <= bid:
            spread = mid * self.synthetic_spread_pct
        else:
            spread = ask - bid

        cross = self.spread_pct * (spread / 2.0)
        if roll_tested:
            cross *= self.intraday_roll_penalty

        if direction in ("sell_to_open", "sell_to_close"):
            return max(mid - cross, 0.01)
        return mid + cross
