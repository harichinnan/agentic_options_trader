"""Minimal Student-t Hidden Markov Model for regime detection.

This is a *research-grade* implementation — deliberately simple, pure
numpy, with Student-t emissions to capture fat tails. The Phase 0 memo
produces the production-grade artifact with proper EM + validation; this
module exists so Phase 2 code has a loadable model interface from day 1.

Regimes (3 by default):
  0 = calm / low-vol normal
  1 = elevated / transition
  2 = crisis / high-vol

Emissions per regime: univariate Student-t over daily log returns
(annualized via sqrt(252)). Features are the raw returns only in this
minimal version; a production fit would add VIX level, term-structure,
MOVE, credit spreads per spec 7.5.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.special import gammaln
from scipy.stats import t as student_t


@dataclass
class StudentTHMMParams:
    """Frozen parameters of a fitted HMM."""

    n_regimes: int
    initial_probs: np.ndarray  # (K,)
    transition_matrix: np.ndarray  # (K, K)
    # Per-regime Student-t params
    means: np.ndarray  # (K,)  daily return mean
    scales: np.ndarray  # (K,)  daily return scale
    dofs: np.ndarray  # (K,)  degrees of freedom

    @property
    def n(self) -> int:
        return self.n_regimes


@dataclass
class StudentTHMM:
    """Fit, infer, and generate from a 3-regime Student-t HMM."""

    n_regimes: int = 3
    max_iter: int = 50
    tol: float = 1e-4
    random_state: int = 42
    params: StudentTHMMParams | None = None
    fit_log_likelihood: list[float] = field(default_factory=list)

    # ---- Fitting (minimal EM; freeze-and-init heuristic for interpretability) --

    def fit(self, returns: np.ndarray) -> "StudentTHMM":
        """Fit via a simplified EM with interpretable regime initialization.

        We initialize regimes by sorting observed vol into K quantiles so the
        regime labels are stable: regime 0 = low vol, K-1 = high vol. This
        avoids the Hungarian-matching headache per spec 7.5 for our minimal fit.
        """
        returns = np.asarray(returns, dtype=float).ravel()
        n = len(returns)
        if n < 50:
            raise ValueError("need >=50 observations to fit")
        rng = np.random.default_rng(self.random_state)

        # Initialize regimes by quantile of absolute returns (proxy for vol bucket)
        quantiles = np.quantile(np.abs(returns), np.linspace(0, 1, self.n_regimes + 1))
        regime_assignment = np.zeros(n, dtype=int)
        for i in range(self.n_regimes):
            lo, hi = quantiles[i], quantiles[i + 1]
            mask = (np.abs(returns) >= lo) & (np.abs(returns) <= hi)
            regime_assignment[mask] = i

        # Initial emission params per regime
        means = np.zeros(self.n_regimes)
        scales = np.zeros(self.n_regimes)
        dofs = np.full(self.n_regimes, 6.0)  # conservative fat-tail prior
        for k in range(self.n_regimes):
            rk = returns[regime_assignment == k]
            if len(rk) >= 2:
                means[k] = rk.mean()
                scales[k] = max(rk.std(ddof=1), 1e-6)
            else:
                means[k] = 0.0
                scales[k] = 0.01

        # Initial transition matrix: sticky, with small cross-regime probability
        transition_matrix = np.eye(self.n_regimes) * 0.90
        transition_matrix += (1 - np.eye(self.n_regimes)) * (0.10 / (self.n_regimes - 1))

        initial_probs = np.full(self.n_regimes, 1.0 / self.n_regimes)

        self.params = StudentTHMMParams(
            n_regimes=self.n_regimes,
            initial_probs=initial_probs,
            transition_matrix=transition_matrix,
            means=means,
            scales=scales,
            dofs=dofs,
        )

        # A handful of Baum-Welch-style updates on Student-t emissions.
        # Kept simple; full EM with Student-t ECM is in the Phase 0 memo.
        prev_ll = -np.inf
        for iteration in range(self.max_iter):
            log_probs = self._log_emission(returns)
            ll, posterior = self._forward_backward(log_probs)
            self.fit_log_likelihood.append(ll)

            # M-step: update means and scales from posterior-weighted moments
            for k in range(self.n_regimes):
                w = posterior[:, k]
                w_sum = w.sum()
                if w_sum <= 1e-12:
                    continue
                means[k] = float((w * returns).sum() / w_sum)
                var = float((w * (returns - means[k]) ** 2).sum() / w_sum)
                scales[k] = max(np.sqrt(var), 1e-6)

            # Update transition matrix from expected joint
            joint = self._expected_joint(log_probs, posterior)
            transition_matrix = joint / np.clip(joint.sum(axis=1, keepdims=True), 1e-12, None)

            self.params = StudentTHMMParams(
                n_regimes=self.n_regimes,
                initial_probs=posterior[0] / posterior[0].sum(),
                transition_matrix=transition_matrix,
                means=means,
                scales=scales,
                dofs=dofs,
            )

            if abs(ll - prev_ll) < self.tol:
                break
            prev_ll = ll
        return self

    # ---- Inference ---------------------------------------------------------

    def infer_regime_probs(self, returns: np.ndarray) -> np.ndarray:
        """Forward-backward smoothed posterior over regimes. Shape (T, K)."""
        self._require_fit()
        log_probs = self._log_emission(np.asarray(returns, dtype=float).ravel())
        _, posterior = self._forward_backward(log_probs)
        return posterior

    def most_likely_regime(self, returns: np.ndarray) -> np.ndarray:
        """Viterbi-style argmax of smoothed posterior (not true Viterbi; good enough)."""
        return np.argmax(self.infer_regime_probs(returns), axis=1)

    # ---- Generative --------------------------------------------------------

    def sample_paths(
        self,
        n_paths: int,
        n_days: int,
        *,
        initial_regime_probs: np.ndarray | None = None,
        rng: np.random.Generator | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate (regime_sequences, returns) of shape (n_paths, n_days).

        If `initial_regime_probs` is None, use the fitted initial distribution.
        """
        self._require_fit()
        p = self.params
        assert p is not None
        rng = rng or np.random.default_rng(self.random_state)
        initial = initial_regime_probs if initial_regime_probs is not None else p.initial_probs

        regimes = np.zeros((n_paths, n_days), dtype=np.int32)
        returns = np.zeros((n_paths, n_days))

        # Vectorized first-day regime
        regimes[:, 0] = rng.choice(p.n_regimes, size=n_paths, p=initial)
        for t in range(1, n_days):
            # Vectorized transition: for each path, sample next regime given current
            for k in range(p.n_regimes):
                mask = regimes[:, t - 1] == k
                count = int(mask.sum())
                if count == 0:
                    continue
                regimes[mask, t] = rng.choice(p.n_regimes, size=count, p=p.transition_matrix[k])

        # Sample returns per regime (vectorized by regime)
        for k in range(p.n_regimes):
            mask = regimes == k
            count = int(mask.sum())
            if count == 0:
                continue
            # Student-t with location=mean, scale=scale, df=dof
            raw = student_t.rvs(df=p.dofs[k], size=count, random_state=rng)
            returns[mask] = p.means[k] + p.scales[k] * raw
        return regimes, returns

    # ---- Internals ---------------------------------------------------------

    def _require_fit(self) -> None:
        if self.params is None:
            raise RuntimeError("HMM not fitted. Call .fit() first.")

    def _log_emission(self, returns: np.ndarray) -> np.ndarray:
        """Per-timestep, per-regime log density. Shape (T, K)."""
        p = self.params
        assert p is not None
        T = len(returns)
        out = np.zeros((T, p.n_regimes))
        for k in range(p.n_regimes):
            # Student-t log pdf
            df = p.dofs[k]
            loc = p.means[k]
            sc = p.scales[k]
            z = (returns - loc) / sc
            c = gammaln((df + 1) / 2) - gammaln(df / 2) - 0.5 * np.log(df * np.pi) - np.log(sc)
            out[:, k] = c - 0.5 * (df + 1) * np.log(1 + (z * z) / df)
        return out

    def _forward_backward(
        self, log_probs: np.ndarray
    ) -> tuple[float, np.ndarray]:
        p = self.params
        assert p is not None
        T, K = log_probs.shape
        log_trans = np.log(np.clip(p.transition_matrix, 1e-30, None))
        log_init = np.log(np.clip(p.initial_probs, 1e-30, None))

        # Forward
        alpha = np.zeros((T, K))
        alpha[0] = log_init + log_probs[0]
        for t in range(1, T):
            for k in range(K):
                alpha[t, k] = log_probs[t, k] + _logsumexp(alpha[t - 1] + log_trans[:, k])

        log_likelihood = float(_logsumexp(alpha[-1]))

        # Backward
        beta = np.zeros((T, K))
        for t in range(T - 2, -1, -1):
            for k in range(K):
                beta[t, k] = _logsumexp(
                    log_trans[k, :] + log_probs[t + 1] + beta[t + 1]
                )

        # Smoothed posterior
        log_posterior = alpha + beta
        log_posterior -= _logsumexp(log_posterior, axis=1, keepdims=True)
        posterior = np.exp(log_posterior)
        return log_likelihood, posterior

    def _expected_joint(
        self, log_probs: np.ndarray, posterior: np.ndarray
    ) -> np.ndarray:
        p = self.params
        assert p is not None
        K = p.n_regimes
        joint = np.zeros((K, K))
        for t in range(len(log_probs) - 1):
            for i in range(K):
                for j in range(K):
                    joint[i, j] += posterior[t, i] * p.transition_matrix[i, j] * np.exp(log_probs[t + 1, j])
        return joint


def _logsumexp(a: np.ndarray, axis=None, keepdims=False):
    """Numerically stable log(sum(exp(a))). Returns scalar when axis=None."""
    if axis is None:
        amax = np.max(a)
        if not np.isfinite(amax):
            amax = 0.0
        return float(np.log(np.sum(np.exp(a - amax))) + amax)

    amax = np.max(a, axis=axis, keepdims=True)
    amax = np.where(np.isfinite(amax), amax, 0.0)
    out = np.log(np.sum(np.exp(a - amax), axis=axis, keepdims=True)) + amax
    if not keepdims:
        out = np.squeeze(out, axis=axis)
    return out
