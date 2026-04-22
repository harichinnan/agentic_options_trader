"""Tests for semantic cross-field validation."""

from __future__ import annotations

import pytest

from thetakit.dsl.loader import get_template
from thetakit.dsl.validator import ValidationError, validate_strategy


def _yaml_from(overrides: dict | None = None, extends: str = "wheel") -> str:
    """Build a small YAML snippet extending a known-good template."""
    lines = [f"extends: {extends}", "name: test"]
    if overrides:
        import yaml as _yaml
        overrides_yaml = _yaml.dump(overrides, default_flow_style=False)
        lines.append(overrides_yaml)
    return "\n".join(lines)


class TestBundledTemplatesPassValidation:
    """All 5 bundled templates should validate (may have warnings but no errors)."""

    @pytest.mark.parametrize(
        "name",
        [
            "wheel",
            "iron_condor_spy",
            "credit_spread_equities",
            "covered_call_basic",
            "csp_dividend_stocks",
        ],
    )
    def test_template_validates(self, name: str) -> None:
        strategy = validate_strategy(get_template(name))
        assert strategy.name


class TestSemanticChecks:
    def test_exit_dte_close_ge_entry_dte_is_error(self) -> None:
        yaml_text = _yaml_from({
            "exits": [{"dte_close": 60}],  # wheel has dte_target=45
        })
        with pytest.raises(ValidationError) as exc:
            validate_strategy(yaml_text)
        assert any("dte_close" in i.path for i in exc.value.issues)

    def test_empty_symbols_list_is_error(self) -> None:
        yaml_text = _yaml_from({"entry": {"symbols": []}})
        with pytest.raises(ValidationError) as exc:
            validate_strategy(yaml_text)
        assert any(i.path == "entry.symbols" for i in exc.value.issues)

    def test_profit_target_gte_1_is_error(self) -> None:
        yaml_text = """
        extends: wheel
        name: bad-exit
        exits:
          - profit_target_pct: 1.0
        """
        # schema allows le=1.0 but semantic check flags == 1.0
        # Actually schema is le=1.0, so 1.0 is within; semantic check is >=1.0 → triggers
        with pytest.raises(ValidationError) as exc:
            validate_strategy(yaml_text)
        assert any("profit_target" in i.path for i in exc.value.issues)

    def test_cc_high_delta_is_warning_not_error(self) -> None:
        yaml_text = """
        extends: covered_call_basic
        name: aggressive-cc
        entry:
          delta_target: 0.45
        """
        # Should pass (warning only)
        strategy = validate_strategy(yaml_text)
        assert strategy.entry.delta_target == 0.45

    def test_cc_high_delta_fails_in_strict_mode(self) -> None:
        yaml_text = """
        extends: covered_call_basic
        name: aggressive-cc
        entry:
          delta_target: 0.45
        """
        with pytest.raises(ValidationError) as exc:
            validate_strategy(yaml_text, warnings_as_errors=True)
        assert any(i.severity == "warning" for i in exc.value.issues)

    def test_iron_condor_high_delta_is_warning(self) -> None:
        yaml_text = """
        extends: iron_condor_spy
        name: wide-ic
        entry:
          delta_target: 0.35
        """
        # Passes (warning only) but strict mode fails
        validate_strategy(yaml_text)  # no raise
        with pytest.raises(ValidationError):
            validate_strategy(yaml_text, warnings_as_errors=True)


class TestValidationErrorFormatting:
    def test_validation_error_str_includes_all_issues(self) -> None:
        yaml_text = _yaml_from({"entry": {"symbols": []}})
        with pytest.raises(ValidationError) as exc:
            validate_strategy(yaml_text)
        rendered = str(exc.value)
        assert "entry.symbols" in rendered

    def test_pydantic_error_becomes_validation_error(self) -> None:
        yaml_text = """
        name: bad
        entry:
          strategy: CSP
          delta_target: 0.99
          dte_target: 45
          symbols: [SPY]
        sizing:
          mode: fixed_contracts
          contracts: 1
        exits:
          - profit_target_pct: 0.5
        """
        with pytest.raises(ValidationError) as exc:
            validate_strategy(yaml_text)
        # delta_target=0.99 violates schema (le=0.5)
        assert any("delta_target" in i.path for i in exc.value.issues)
