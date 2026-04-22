"""Schema-level (Pydantic) validation tests for the DSL."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from thetakit.dsl.schema import (
    EntryRule,
    ExitRule,
    PositionSizing,
    RiskConstraints,
    RollRule,
    Strategy,
    StrategyType,
)


def _minimal_csp() -> dict:
    """A minimal, valid CSP strategy dict for use as a base in tests."""
    return {
        "name": "test-csp",
        "entry": {
            "strategy": "CSP",
            "delta_target": 0.30,
            "dte_target": 45,
            "symbols": ["SPY"],
        },
        "sizing": {"mode": "fixed_contracts", "contracts": 1},
        "rolls": [],
        "exits": [{"profit_target_pct": 0.5}],
        "risk": {},
    }


class TestEntryRule:
    def test_valid_csp_parses(self) -> None:
        e = EntryRule(strategy=StrategyType.CSP, delta_target=0.30, dte_target=45, symbols=["SPY"])
        assert e.delta_target == 0.30
        assert e.strategy is StrategyType.CSP

    def test_delta_target_below_range_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            EntryRule(strategy="CSP", delta_target=0.01, dte_target=45, symbols=["SPY"])

    def test_delta_target_above_range_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            EntryRule(strategy="CSP", delta_target=0.6, dte_target=45, symbols=["SPY"])

    def test_dte_target_zero_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            EntryRule(strategy="CSP", delta_target=0.30, dte_target=0, symbols=["SPY"])

    def test_unknown_strategy_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            EntryRule(strategy="NOPE", delta_target=0.30, dte_target=45, symbols=["SPY"])  # type: ignore[arg-type]

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            EntryRule.model_validate({
                "strategy": "CSP",
                "delta_target": 0.30,
                "dte_target": 45,
                "symbols": ["SPY"],
                "unknown_field": True,
            })


class TestPositionSizing:
    def test_fixed_contracts_requires_contracts(self) -> None:
        with pytest.raises(PydanticValidationError):
            PositionSizing(mode="fixed_contracts")

    def test_pct_bp_requires_pct(self) -> None:
        with pytest.raises(PydanticValidationError):
            PositionSizing(mode="pct_bp")

    def test_kelly_requires_kelly_fraction(self) -> None:
        with pytest.raises(PydanticValidationError):
            PositionSizing(mode="kelly_lite")

    def test_valid_fixed(self) -> None:
        p = PositionSizing(mode="fixed_contracts", contracts=2)
        assert p.contracts == 2


class TestRollRule:
    def test_delta_breach_requires_threshold(self) -> None:
        with pytest.raises(PydanticValidationError):
            RollRule(trigger="delta_breach")

    def test_dte_threshold_requires_value(self) -> None:
        with pytest.raises(PydanticValidationError):
            RollRule(trigger="dte_threshold")

    def test_short_strike_tested_no_extra_fields_needed(self) -> None:
        r = RollRule(trigger="short_strike_tested")
        assert r.target_dte == 45


class TestExitRule:
    def test_exit_needs_at_least_one_trigger(self) -> None:
        with pytest.raises(PydanticValidationError):
            ExitRule()

    def test_profit_target_only(self) -> None:
        e = ExitRule(profit_target_pct=0.5)
        assert e.profit_target_pct == 0.5

    def test_dte_close_only(self) -> None:
        e = ExitRule(dte_close=21)
        assert e.dte_close == 21


class TestRiskConstraints:
    def test_defaults(self) -> None:
        r = RiskConstraints()
        assert r.max_concurrent_positions == 20
        assert r.initial_capital == 100_000

    def test_negative_capital_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            RiskConstraints(initial_capital=-1)


class TestStrategy:
    def test_minimal_csp_parses(self) -> None:
        s = Strategy.model_validate(_minimal_csp())
        assert s.name == "test-csp"
        assert s.entry.strategy is StrategyType.CSP

    def test_spread_requires_wing_width(self) -> None:
        data = _minimal_csp()
        data["entry"]["strategy"] = "BullPutSpread"
        with pytest.raises(PydanticValidationError) as exc:
            Strategy.model_validate(data)
        assert "wing_width" in str(exc.value)

    def test_spread_with_wing_width_parses(self) -> None:
        data = _minimal_csp()
        data["entry"]["strategy"] = "BullPutSpread"
        data["entry"]["wing_width"] = 5.0
        s = Strategy.model_validate(data)
        assert s.entry.wing_width == 5.0

    def test_needs_at_least_one_exit(self) -> None:
        data = _minimal_csp()
        data["exits"] = []
        with pytest.raises(PydanticValidationError):
            Strategy.model_validate(data)

    def test_name_required(self) -> None:
        data = _minimal_csp()
        del data["name"]
        with pytest.raises(PydanticValidationError):
            Strategy.model_validate(data)
