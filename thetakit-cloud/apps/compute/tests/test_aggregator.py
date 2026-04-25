"""Aggregator tests."""

from __future__ import annotations

import pytest

from compute.aggregator import PathOutcome, aggregate


def _outcome(ret: float, dd: float = 0.0, regime: int = 0) -> PathOutcome:
    return PathOutcome(
        path_id=0, total_return_pct=ret, max_drawdown_pct=dd, cagr_pct=ret,
        trades=10, win_rate=70.0, dominant_regime=regime,
    )


class TestAggregator:
    def test_empty_input_returns_zeros(self) -> None:
        stats = aggregate([])
        assert stats.n_paths == 0
        assert stats.return_median == 0.0

    def test_basic_percentiles(self) -> None:
        outcomes = [_outcome(r) for r in [-10, -5, 0, 5, 10, 15, 20]]
        stats = aggregate(outcomes)
        assert abs(stats.return_median - 5.0) < 1e-6
        assert stats.return_p05 < stats.return_p25 < stats.return_p75 < stats.return_p95

    def test_cvar_pulls_from_tail(self) -> None:
        outcomes = [_outcome(r) for r in list(range(-50, 51, 5))]
        stats = aggregate(outcomes)
        # CVaR 5% <= p05 (average of worst 5%, which is at or below 5th percentile)
        assert stats.cvar_05 <= stats.return_p05 + 1e-6

    def test_prob_ruin_counts_severe_drawdowns(self) -> None:
        outcomes = [
            _outcome(0, dd=-10), _outcome(0, dd=-30), _outcome(0, dd=-60),
        ]
        stats = aggregate(outcomes)
        # 2/3 of paths have dd <= -25, 1/3 have dd <= -50
        assert stats.prob_ruin_25pct == pytest.approx(2 / 3, abs=1e-6)
        assert stats.prob_ruin_50pct == pytest.approx(1 / 3, abs=1e-6)

    def test_regime_breakdown(self) -> None:
        outcomes = [
            _outcome(10, regime=0), _outcome(12, regime=0),
            _outcome(-5, regime=2), _outcome(-8, regime=2),
        ]
        stats = aggregate(outcomes)
        assert stats.return_by_regime[0] == pytest.approx(11.0)
        assert stats.return_by_regime[2] == pytest.approx(-6.5)

    def test_stress_paths_reported_separately(self) -> None:
        outcomes = [
            _outcome(10), _outcome(5), _outcome(-2),
            PathOutcome(
                path_id=99, total_return_pct=-20, max_drawdown_pct=-25,
                cagr_pct=-20, trades=5, win_rate=20, dominant_regime=2,
                stress_scenario="covid_crash_mar_2020",
            ),
        ]
        stats = aggregate(outcomes)
        assert stats.stress_results == {"covid_crash_mar_2020": -20.0}
        # MC median excludes the stress path (it's -2/5/10 → median 5)
        assert stats.return_median == pytest.approx(5.0)
