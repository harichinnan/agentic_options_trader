"""Tests for the strategy loader and template system."""

from __future__ import annotations

import pytest

from thetakit.dsl.loader import (
    StrategyLoadError,
    _deep_merge,  # pyright: ignore[reportPrivateUsage]
    _resolve_extends,  # pyright: ignore[reportPrivateUsage]
    get_template,
    list_templates,
    load_strategy,
)

EXPECTED_TEMPLATES = {
    "wheel",
    "iron_condor_spy",
    "credit_spread_equities",
    "covered_call_basic",
    "csp_dividend_stocks",
}


class TestTemplateDiscovery:
    def test_lists_five_bundled_templates(self) -> None:
        templates = set(list_templates())
        assert EXPECTED_TEMPLATES.issubset(templates), (
            f"missing templates: {EXPECTED_TEMPLATES - templates}"
        )

    def test_get_template_returns_yaml(self) -> None:
        text = get_template("wheel")
        assert "name: Wheel" in text
        assert "strategy: CSP" in text

    def test_get_template_unknown_raises(self) -> None:
        with pytest.raises(StrategyLoadError) as exc:
            get_template("nope-does-not-exist")
        assert "not found" in str(exc.value)


class TestLoadStrategy:
    def test_loads_valid_minimal_yaml(self) -> None:
        yaml_text = """
        name: simple
        entry:
          strategy: CSP
          delta_target: 0.30
          dte_target: 45
          symbols: [SPY]
        sizing:
          mode: fixed_contracts
          contracts: 1
        rolls: []
        exits:
          - profit_target_pct: 0.5
        """
        s = load_strategy(yaml_text)
        assert s.name == "simple"

    def test_empty_file_rejected(self) -> None:
        with pytest.raises(StrategyLoadError):
            load_strategy("")

    def test_non_mapping_top_level_rejected(self) -> None:
        with pytest.raises(StrategyLoadError):
            load_strategy("- just\n- a\n- list")

    def test_yaml_syntax_error_surfaced(self) -> None:
        with pytest.raises(StrategyLoadError) as exc:
            load_strategy("{invalid: :yaml:")
        assert "YAML parse error" in str(exc.value)


class TestTemplateInheritance:
    def test_extends_wheel_overrides_symbols(self) -> None:
        yaml_text = """
        extends: wheel
        name: wheel-custom
        entry:
          symbols: [TQQQ]
        """
        s = load_strategy(yaml_text)
        assert s.name == "wheel-custom"
        # Inherited from wheel
        assert s.entry.strategy.value == "CSP"
        assert s.entry.delta_target == 0.30
        assert s.entry.dte_target == 45
        # Overridden
        assert s.entry.symbols == ["TQQQ"]

    def test_extends_removes_extends_key_after_merge(self) -> None:
        yaml_text = """
        extends: wheel
        name: derived
        """
        s = load_strategy(yaml_text)
        assert s.extends is None

    def test_deep_merge_merges_nested_dicts(self) -> None:
        base = {"entry": {"delta_target": 0.30, "dte_target": 45, "symbols": ["SPY"]}}
        override = {"entry": {"delta_target": 0.20}, "name": "new"}
        merged = _deep_merge(base, override)
        assert merged["entry"]["delta_target"] == 0.20  # overridden
        assert merged["entry"]["dte_target"] == 45  # preserved
        assert merged["entry"]["symbols"] == ["SPY"]  # preserved
        assert merged["name"] == "new"

    def test_deep_merge_replaces_lists_wholesale(self) -> None:
        base = {"symbols": ["SPY", "QQQ"]}
        override = {"symbols": ["IWM"]}
        merged = _deep_merge(base, override)
        assert merged["symbols"] == ["IWM"]

    def test_circular_extends_detected(self) -> None:
        # Hard to trigger with real templates, so exercise _resolve_extends directly
        with pytest.raises(StrategyLoadError) as exc:
            _resolve_extends({"extends": "wheel"}, _seen={"wheel"})
        assert "circular" in str(exc.value)


class TestBundledTemplatesLoad:
    """Sanity: every bundled template must load cleanly without semantic checks."""

    @pytest.mark.parametrize("name", sorted(EXPECTED_TEMPLATES))
    def test_template_loads(self, name: str) -> None:
        s = load_strategy(get_template(name))
        assert s.name
        assert s.entry is not None
        assert len(s.exits) >= 1
