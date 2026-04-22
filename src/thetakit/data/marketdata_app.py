"""MarketData.app adapter — Phase 1 stub.

Wiring for MarketData.app is intentionally a thin stub in Phase 1. Users
who have an API key can extend this class or use the LocalParquetAdapter
with data they've downloaded separately. The scaffold here documents the
URL shapes and response schemas so completing the integration is tractable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from thetakit.data.adapter import CalendarEvent, OptionQuote, UnderlyingBar
from thetakit.data.calendar import CalendarProvider


@dataclass
class MarketDataAppAdapter:
    """Placeholder adapter. Raises NotImplementedError on network-dependent calls.

    Real implementation would hit:
      - https://api.marketdata.app/v1/stocks/candles/D/{symbol}/
      - https://api.marketdata.app/v1/options/chain/{symbol}/
    """

    api_token: str
    calendar: CalendarProvider = field(default_factory=CalendarProvider.default)

    def _not_impl(self, method: str):
        raise NotImplementedError(
            f"MarketDataAppAdapter.{method} is stubbed in Phase 1. "
            "Use SyntheticDataAdapter for tests or LocalParquetAdapter with "
            "pre-downloaded data. See docs/architecture.md."
        )

    def get_trading_days(self, start: date, end: date) -> list[date]:
        self._not_impl("get_trading_days")

    def get_underlying_bar(self, symbol: str, on: date) -> UnderlyingBar | None:
        self._not_impl("get_underlying_bar")

    def get_option_chain(
        self,
        symbol: str,
        on: date,
        *,
        min_dte: int = 0,
        max_dte: int = 120,
        option_type: str | None = None,
    ) -> list[OptionQuote]:
        self._not_impl("get_option_chain")

    def get_calendar_events(
        self,
        symbols: list[str] | None,
        start: date,
        end: date,
        event_types: list[str] | None = None,
    ) -> list[CalendarEvent]:
        return self.calendar.events_in_range(
            start, end, symbols=symbols, event_types=event_types
        )
