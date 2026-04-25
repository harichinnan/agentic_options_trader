"""Student-t HMM smoke tests: shape, determinism, regime stability."""

from __future__ import annotations

import numpy as np
import pytest

from compute.hmm.model import StudentTHMM


@pytest.fixture
def synthetic_returns() -> np.ndarray:
    """Two-regime synthetic returns: long calm + short crisis."""
    rng = np.random.default_rng(0)
    calm = rng.normal(0.0005, 0.008, size=1500)
    crisis = rng.normal(-0.002, 0.035, size=80)
    # Splice: crisis in the middle
    return np.concatenate([calm[:750], crisis, calm[750:]])


class TestHMMFit:
    def test_fits_without_error(self, synthetic_returns: np.ndarray) -> None:
        hmm = StudentTHMM(n_regimes=3, max_iter=15, random_state=42)
        hmm.fit(synthetic_returns)
        assert hmm.params is not None
        assert hmm.params.n_regimes == 3

    def test_regime_labels_are_vol_ordered(self, synthetic_returns: np.ndarray) -> None:
        hmm = StudentTHMM(n_regimes=3, max_iter=15, random_state=42).fit(synthetic_returns)
        assert hmm.params is not None
        scales = hmm.params.scales
        # Regime 0 should be the lowest vol by initialization
        assert scales[0] <= scales[-1]

    def test_transition_matrix_rows_sum_to_one(self, synthetic_returns: np.ndarray) -> None:
        hmm = StudentTHMM(n_regimes=3, max_iter=15).fit(synthetic_returns)
        assert hmm.params is not None
        for row in hmm.params.transition_matrix:
            assert abs(row.sum() - 1.0) < 1e-6


class TestHMMInfer:
    def test_infer_returns_posterior_shape(self, synthetic_returns: np.ndarray) -> None:
        hmm = StudentTHMM(n_regimes=3, max_iter=10).fit(synthetic_returns)
        post = hmm.infer_regime_probs(synthetic_returns)
        assert post.shape == (len(synthetic_returns), 3)
        # Each row sums to ~1
        sums = post.sum(axis=1)
        assert np.allclose(sums, 1.0, atol=1e-3)


class TestHMMGenerate:
    def test_sample_paths_shapes(self, synthetic_returns: np.ndarray) -> None:
        hmm = StudentTHMM(n_regimes=3, max_iter=10).fit(synthetic_returns)
        regimes, rets = hmm.sample_paths(n_paths=10, n_days=50)
        assert regimes.shape == (10, 50)
        assert rets.shape == (10, 50)

    def test_sample_paths_deterministic_with_same_seed(self, synthetic_returns: np.ndarray) -> None:
        hmm = StudentTHMM(n_regimes=3, max_iter=10, random_state=7).fit(synthetic_returns)
        rng_a = np.random.default_rng(123)
        a = hmm.sample_paths(5, 20, rng=rng_a)
        rng_b = np.random.default_rng(123)
        b = hmm.sample_paths(5, 20, rng=rng_b)
        assert np.array_equal(a[0], b[0])
        assert np.allclose(a[1], b[1])

    def test_samples_stay_finite(self, synthetic_returns: np.ndarray) -> None:
        hmm = StudentTHMM(n_regimes=3, max_iter=5).fit(synthetic_returns)
        regimes, rets = hmm.sample_paths(50, 30)
        assert np.all(np.isfinite(rets))
