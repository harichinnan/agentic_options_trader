"""Bundled calendar events (FOMC, CPI, OPEX) + per-symbol earnings stubs.

Dates bundled here are a static, pre-loaded snapshot. Real vendors would
update dynamically, but for Phase 1 we ship a credible set of known dates
so that event-proximity filters have something to operate against in
tests and reference backtests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from thetakit.data.adapter import CalendarEvent


# --- Bundled static datasets (representative, not exhaustive) -----------------

FOMC_MEETING_DATES_2023_2026: list[str] = [
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26",
    "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31",
    "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30",
    "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29",
]

# OPEX = 3rd Friday of each month (approximate)
OPEX_DATES_2023_2026: list[str] = [
    "2023-01-20", "2023-02-17", "2023-03-17", "2023-04-21", "2023-05-19",
    "2023-06-16", "2023-07-21", "2023-08-18", "2023-09-15", "2023-10-20",
    "2023-11-17", "2023-12-15",
    "2024-01-19", "2024-02-16", "2024-03-15", "2024-04-19", "2024-05-17",
    "2024-06-21", "2024-07-19", "2024-08-16", "2024-09-20", "2024-10-18",
    "2024-11-15", "2024-12-20",
    "2025-01-17", "2025-02-21", "2025-03-21", "2025-04-17", "2025-05-16",
    "2025-06-20", "2025-07-18", "2025-08-15", "2025-09-19", "2025-10-17",
    "2025-11-21", "2025-12-19",
    "2026-01-16", "2026-02-20", "2026-03-20", "2026-04-17",
]

# CPI releases (typically 2nd Tuesday/Wednesday of each month)
CPI_DATES_2023_2026: list[str] = [
    "2023-01-12", "2023-02-14", "2023-03-14", "2023-04-12", "2023-05-10",
    "2023-06-13", "2023-07-12", "2023-08-10", "2023-09-13", "2023-10-12",
    "2023-11-14", "2023-12-12",
    "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10", "2024-05-15",
    "2024-06-12", "2024-07-11", "2024-08-14", "2024-09-11", "2024-10-10",
    "2024-11-13", "2024-12-11",
    "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10", "2025-05-13",
    "2025-06-11", "2025-07-15", "2025-08-12", "2025-09-11", "2025-10-15",
    "2025-11-13", "2025-12-10",
    "2026-01-14", "2026-02-11", "2026-03-11", "2026-04-15",
]

# NFP = first Friday of each month (approximate)
NFP_DATES_2023_2026: list[str] = [
    "2023-01-06", "2023-02-03", "2023-03-10", "2023-04-07", "2023-05-05",
    "2023-06-02", "2023-07-07", "2023-08-04", "2023-09-01", "2023-10-06",
    "2023-11-03", "2023-12-08",
    "2024-01-05", "2024-02-02", "2024-03-08", "2024-04-05", "2024-05-03",
    "2024-06-07", "2024-07-05", "2024-08-02", "2024-09-06", "2024-10-04",
    "2024-11-01", "2024-12-06",
    "2025-01-10", "2025-02-07", "2025-03-07", "2025-04-04", "2025-05-02",
    "2025-06-06", "2025-07-03", "2025-08-01", "2025-09-05", "2025-10-03",
    "2025-11-07", "2025-12-05",
    "2026-01-09", "2026-02-06", "2026-03-06", "2026-04-03",
]


def load_bundled_calendar() -> list[CalendarEvent]:
    """Return all bundled market-wide calendar events."""
    events: list[CalendarEvent] = []
    for d in FOMC_MEETING_DATES_2023_2026:
        events.append(CalendarEvent(date=d, event_type="fomc", detail="FOMC meeting"))
    for d in OPEX_DATES_2023_2026:
        events.append(CalendarEvent(date=d, event_type="opex", detail="Monthly OPEX"))
    for d in CPI_DATES_2023_2026:
        events.append(CalendarEvent(date=d, event_type="cpi", detail="CPI release"))
    for d in NFP_DATES_2023_2026:
        events.append(CalendarEvent(date=d, event_type="nfp", detail="NFP release"))
    return events


@dataclass
class CalendarProvider:
    """Keeps the bundled events + accepts caller-supplied per-symbol events."""

    market_events: list[CalendarEvent]
    symbol_events: dict[str, list[CalendarEvent]]

    @classmethod
    def default(cls) -> CalendarProvider:
        return cls(market_events=load_bundled_calendar(), symbol_events={})

    def add_symbol_events(self, symbol: str, events: Iterable[CalendarEvent]) -> None:
        self.symbol_events.setdefault(symbol, []).extend(events)

    def events_in_range(
        self,
        start: date,
        end: date,
        *,
        symbols: list[str] | None = None,
        event_types: list[str] | None = None,
    ) -> list[CalendarEvent]:
        lo, hi = start.isoformat(), end.isoformat()
        types = set(event_types) if event_types else None
        out: list[CalendarEvent] = []

        for ev in self.market_events:
            if lo <= ev.date <= hi and (types is None or ev.event_type in types):
                out.append(ev)

        if symbols:
            for sym in symbols:
                for ev in self.symbol_events.get(sym, []):
                    if lo <= ev.date <= hi and (types is None or ev.event_type in types):
                        out.append(ev)

        return sorted(out, key=lambda e: (e.date, e.event_type))

    def days_until_next_event(
        self, on: date, *, symbol: str | None = None, event_types: list[str] | None = None
    ) -> dict[str, int]:
        """Return {event_type: days_until_next_event} for types with upcoming events."""
        today = on.isoformat()
        types = set(event_types) if event_types else None
        nearest: dict[str, int] = {}

        candidates = list(self.market_events)
        if symbol:
            candidates.extend(self.symbol_events.get(symbol, []))

        for ev in candidates:
            if types is not None and ev.event_type not in types:
                continue
            if ev.date < today:
                continue
            delta = (date.fromisoformat(ev.date) - on).days
            cur = nearest.get(ev.event_type)
            if cur is None or delta < cur:
                nearest[ev.event_type] = delta
        return nearest
