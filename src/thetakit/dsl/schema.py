"""Pydantic v2 schema for the thetakit strategy DSL.

A Strategy is a complete specification of a premium-selling playbook:
entry criteria, position sizing, roll triggers, exit criteria, and
portfolio-level risk constraints. Strategies are authored in YAML and
may inherit from bundled templates via the `extends` field.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrategyType(str, Enum):
    """Supported strategy types. Drives semantic validation downstream."""

    CSP = "CSP"  # Cash-Secured Put
    CC = "CC"  # Covered Call
    BULL_PUT_SPREAD = "BullPutSpread"
    BEAR_CALL_SPREAD = "BearCallSpread"
    IRON_CONDOR = "IronCondor"


class SymbolFilter(BaseModel):
    """Dynamic symbol selection (e.g., by liquidity or sector)."""

    model_config = ConfigDict(extra="forbid")

    min_avg_volume: int | None = Field(
        default=None, ge=0, description="Min 30-day avg option volume"
    )
    min_iv_rank: float | None = Field(default=None, ge=0, le=100, description="Min IV rank 0-100")
    sectors: list[str] | None = None
    exclude: list[str] = Field(default_factory=list, description="Symbols to exclude")


class EntryRule(BaseModel):
    """Criteria for opening a new position."""

    model_config = ConfigDict(extra="forbid")

    strategy: StrategyType
    delta_target: float = Field(..., ge=0.05, le=0.5, description="Absolute delta target")
    delta_tolerance: float = Field(default=0.05, ge=0.0, le=0.25)
    dte_target: int = Field(..., ge=7, le=90, description="Days to expiration target")
    dte_tolerance: int = Field(default=7, ge=0, le=30)
    min_iv_rank: float | None = Field(default=None, ge=0, le=100)
    symbols: list[str] | SymbolFilter = Field(..., description="Explicit list or dynamic filter")

    # Event proximity filters
    skip_if_earnings_within_days: int | None = Field(default=None, ge=0, le=30)
    skip_if_fomc_within_days: int | None = Field(default=None, ge=0, le=14)
    skip_if_cpi_within_days: int | None = Field(default=None, ge=0, le=14)
    skip_if_ex_div_within_days: int | None = Field(default=None, ge=0, le=14)

    # Spread-specific fields (required for spread strategies, validated downstream)
    wing_width: float | None = Field(
        default=None, gt=0, description="Distance between long/short strike for spreads"
    )


class PositionSizing(BaseModel):
    """How many contracts to open per entry signal."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["fixed_contracts", "pct_bp", "kelly_lite"]
    contracts: int | None = Field(default=None, ge=1, description="For fixed_contracts mode")
    pct_bp: float | None = Field(
        default=None, gt=0, le=1.0, description="Fraction of buying power (0-1)"
    )
    kelly_fraction: float | None = Field(
        default=None, gt=0, le=0.5, description="Fraction of Kelly (for kelly_lite)"
    )

    @model_validator(mode="after")
    def _check_mode_fields(self) -> PositionSizing:
        if self.mode == "fixed_contracts" and self.contracts is None:
            raise ValueError("sizing.contracts is required when mode='fixed_contracts'")
        if self.mode == "pct_bp" and self.pct_bp is None:
            raise ValueError("sizing.pct_bp is required when mode='pct_bp'")
        if self.mode == "kelly_lite" and self.kelly_fraction is None:
            raise ValueError("sizing.kelly_fraction is required when mode='kelly_lite'")
        return self


class RollRule(BaseModel):
    """A single roll trigger. A strategy can have multiple, evaluated in order."""

    model_config = ConfigDict(extra="forbid")

    trigger: Literal["short_strike_tested", "delta_breach", "dte_threshold"]
    delta_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    dte_threshold: int | None = Field(default=None, ge=0, le=90)
    target_dte: int = Field(default=45, ge=7, le=120)
    target_delta: float = Field(default=0.35, ge=0.05, le=0.5)

    @model_validator(mode="after")
    def _check_trigger_fields(self) -> RollRule:
        if self.trigger == "delta_breach" and self.delta_threshold is None:
            raise ValueError("rolls[*].delta_threshold is required when trigger='delta_breach'")
        if self.trigger == "dte_threshold" and self.dte_threshold is None:
            raise ValueError("rolls[*].dte_threshold is required when trigger='dte_threshold'")
        return self


class ExitRule(BaseModel):
    """A single exit trigger. Multiple exits are OR-combined (first hit closes)."""

    model_config = ConfigDict(extra="forbid")

    profit_target_pct: float | None = Field(
        default=None, gt=0, le=1.0, description="Close at X fraction of max profit (0-1)"
    )
    dte_close: int | None = Field(default=None, ge=0, le=90, description="Close at <= this DTE")
    stop_loss_multiplier: float | None = Field(
        default=None, gt=0, description="Close if loss exceeds X times credit received"
    )

    @model_validator(mode="after")
    def _at_least_one_trigger(self) -> ExitRule:
        if (
            self.profit_target_pct is None
            and self.dte_close is None
            and self.stop_loss_multiplier is None
        ):
            raise ValueError(
                "each exit rule must set at least one of: "
                "profit_target_pct, dte_close, stop_loss_multiplier"
            )
        return self


class RiskConstraints(BaseModel):
    """Portfolio-level risk limits. Enforced before opening new positions."""

    model_config = ConfigDict(extra="forbid")

    max_concurrent_positions: int = Field(default=20, ge=1, le=200)
    max_capital_per_symbol_pct: float = Field(default=0.1, gt=0, le=1.0)
    max_portfolio_delta: float | None = Field(default=None, ge=0)
    max_portfolio_vega: float | None = Field(default=None, ge=0)
    max_portfolio_theta: float | None = Field(default=None, description="Min theta (can be negative)")
    initial_capital: float = Field(default=100_000, gt=0)


class Strategy(BaseModel):
    """Complete strategy specification.

    A Strategy is the top-level object loaded from a YAML rule file. It may
    inherit from a bundled template via `extends: <template-name>`, in which
    case the loader merges fields before validation.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    extends: str | None = Field(
        default=None, description="Name of bundled template to inherit from"
    )

    entry: EntryRule
    sizing: PositionSizing
    rolls: list[RollRule] = Field(default_factory=list)
    exits: list[ExitRule] = Field(..., min_length=1)
    risk: RiskConstraints = Field(default_factory=lambda: RiskConstraints())

    @model_validator(mode="after")
    def _spread_needs_wing_width(self) -> Strategy:
        spread_types = {
            StrategyType.BULL_PUT_SPREAD,
            StrategyType.BEAR_CALL_SPREAD,
            StrategyType.IRON_CONDOR,
        }
        if self.entry.strategy in spread_types and self.entry.wing_width is None:
            raise ValueError(
                f"entry.wing_width is required for spread strategy '{self.entry.strategy.value}'"
            )
        return self
