"""Local Parquet data adapter.

Reads pre-downloaded options data from a directory of Parquet files with
a simple naming convention:

    <root>/
      underlying/<SYMBOL>.parquet            # columns: date, open, high, low, close, volume
      options/<SYMBOL>/<YYYY-MM>.parquet     # columns: date, option_ticker, option_type,
                                              #   strike, expiration, mid, bid, ask, volume,
                                              #   open_interest, implied_volatility

Any missing files fall back to returning empty results so callers can use
this adapter for partial datasets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from thetakit.data.adapter import CalendarEvent, OptionQuote, UnderlyingBar
from thetakit.data.calendar import CalendarProvider


@dataclass
class LocalParquetAdapter:
    """DataAdapter that reads Parquet files from a local cache directory."""

    root: Path
    calendar: CalendarProvider = field(default_factory=CalendarProvider.default)

    def __post_init__(self) -> None:
        self.root = Path(self.root)

    def _read_underlying(self, symbol: str):
        try:
            import pyarrow.parquet as pq
        except ImportError as e:
            raise RuntimeError("pyarrow is required for LocalParquetAdapter") from e
        path = self.root / "underlying" / f"{symbol}.parquet"
        if not path.exists():
            return None
        return pq.read_table(path).to_pylist()

    def _read_options_month(self, symbol: str, year_month: str):
        try:
            import pyarrow.parquet as pq
        except ImportError as e:
            raise RuntimeError("pyarrow is required for LocalParquetAdapter") from e
        path = self.root / "options" / symbol / f"{year_month}.parquet"
        if not path.exists():
            return []
        return pq.read_table(path).to_pylist()

    def get_trading_days(self, start: date, end: date) -> list[date]:
        # Derive from any available underlying file; if none, fall back to Mon-Fri
        for sym_path in (self.root / "underlying").glob("*.parquet") if (self.root / "underlying").exists() else []:
            rows = self._read_underlying(sym_path.stem) or []
            days = sorted({r["date"] for r in rows})
            return [date.fromisoformat(d) for d in days if start.isoformat() <= d <= end.isoformat()]
        # fallback
        from datetime import timedelta
        out = []
        d = start
        while d <= end:
            if d.weekday() < 5:
                out.append(d)
            d += timedelta(days=1)
        return out

    def get_underlying_bar(self, symbol: str, on: date) -> UnderlyingBar | None:
        rows = self._read_underlying(symbol) or []
        for r in rows:
            if r["date"] == on.isoformat():
                return UnderlyingBar(
                    date=r["date"],
                    symbol=symbol,
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=int(r["volume"]),
                )
        return None

    def get_option_chain(
        self,
        symbol: str,
        on: date,
        *,
        min_dte: int = 0,
        max_dte: int = 120,
        option_type: str | None = None,
    ) -> list[OptionQuote]:
        ym = on.strftime("%Y-%m")
        rows = self._read_options_month(symbol, ym)
        out: list[OptionQuote] = []
        for r in rows:
            if r["date"] != on.isoformat():
                continue
            if option_type and r["option_type"] != option_type:
                continue
            exp = date.fromisoformat(r["expiration"])
            dte = (exp - on).days
            if dte < min_dte or dte > max_dte:
                continue
            out.append(
                OptionQuote(
                    date=r["date"],
                    symbol=symbol,
                    option_ticker=r["option_ticker"],
                    option_type=r["option_type"],
                    strike=float(r["strike"]),
                    expiration=r["expiration"],
                    mid=float(r["mid"]),
                    bid=float(r.get("bid") or 0) or None,
                    ask=float(r.get("ask") or 0) or None,
                    volume=int(r.get("volume", 0)),
                    open_interest=int(r.get("open_interest", 0)),
                    implied_volatility=r.get("implied_volatility"),
                )
            )
        return out

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
