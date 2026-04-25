"""Smoke test the full eval pipeline end-to-end."""

from __future__ import annotations

import pytest

from compute.eval_runner import EvalInput, run_smoke_eval
from thetakit.dsl import get_template


@pytest.mark.slow
class TestSmokeEval:
    def test_runs_on_wheel_template(self) -> None:
        inp = EvalInput(
            rule_yaml=get_template("wheel"),
            universe=["SPY", "QQQ", "IWM"],
            initial_prices={"SPY": 450, "QQQ": 380, "IWM": 190},
            start="2024-01-02",
            end="2024-02-01",
            seed=7,
        )
        result = run_smoke_eval(inp)
        assert result.eval_type == "smoke"
        assert result.n_paths > 0
        assert result.stats.return_median is not None
