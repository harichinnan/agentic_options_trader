"""Black-Scholes pricing, greeks, and IV solver tests."""

from __future__ import annotations

import math

import pytest

from thetakit.pricing.bsm import bsm_greeks, bsm_price, implied_volatility


class TestBSMPrice:
    def test_atm_call_price_reasonable(self) -> None:
        # ATM 1-month 20% vol call should be roughly 2.3% of spot
        p = bsm_price(s=100, k=100, t=30 / 365, r=0.04, sigma=0.20, option_type="call")
        assert 1.5 < p < 3.5

    def test_deep_itm_call_near_intrinsic(self) -> None:
        p = bsm_price(s=120, k=100, t=7 / 365, r=0.04, sigma=0.20, option_type="call")
        assert p >= 20.0

    def test_deep_otm_put_near_zero(self) -> None:
        p = bsm_price(s=120, k=80, t=7 / 365, r=0.04, sigma=0.20, option_type="put")
        assert p < 0.01

    def test_expired_option_is_intrinsic(self) -> None:
        assert bsm_price(s=105, k=100, t=0, r=0.04, sigma=0.20, option_type="call") == 5.0
        assert bsm_price(s=95, k=100, t=0, r=0.04, sigma=0.20, option_type="put") == 5.0

    def test_put_call_parity(self) -> None:
        s, k, t, r, sigma = 100, 105, 60 / 365, 0.04, 0.25
        c = bsm_price(s, k, t, r, sigma, "call")
        p = bsm_price(s, k, t, r, sigma, "put")
        # c - p == s - k*exp(-rt)   (zero div)
        expected = s - k * math.exp(-r * t)
        assert abs((c - p) - expected) < 1e-6


class TestGreeks:
    def test_call_delta_in_0_1(self) -> None:
        for spot in (80, 100, 120):
            g = bsm_greeks(s=spot, k=100, t=30 / 365, r=0.04, sigma=0.2, option_type="call")
            assert 0 <= g.delta <= 1

    def test_put_delta_negative_and_bounded(self) -> None:
        g = bsm_greeks(s=100, k=100, t=30 / 365, r=0.04, sigma=0.2, option_type="put")
        assert -1 <= g.delta <= 0

    def test_gamma_positive(self) -> None:
        g = bsm_greeks(s=100, k=100, t=30 / 365, r=0.04, sigma=0.2, option_type="call")
        assert g.gamma > 0

    def test_theta_negative_for_long_option(self) -> None:
        g = bsm_greeks(s=100, k=100, t=30 / 365, r=0.04, sigma=0.2, option_type="call")
        assert g.theta < 0

    def test_vega_positive(self) -> None:
        g = bsm_greeks(s=100, k=100, t=30 / 365, r=0.04, sigma=0.2, option_type="call")
        assert g.vega > 0


class TestImpliedVolatility:
    @pytest.mark.parametrize("sigma_true", [0.10, 0.20, 0.35, 0.60])
    def test_roundtrip_iv(self, sigma_true: float) -> None:
        # Generate a synthetic price then recover IV
        s, k, t, r = 100, 105, 45 / 365, 0.04
        price = bsm_price(s, k, t, r, sigma_true, "call")
        recovered = implied_volatility(price, s, k, t, r, "call")
        assert abs(recovered - sigma_true) < 1e-3

    def test_below_intrinsic_returns_nan(self) -> None:
        # Market price below intrinsic is impossible; solver should return NaN
        iv = implied_volatility(0.5, s=110, k=100, t=30 / 365, r=0.04, option_type="call")
        assert math.isnan(iv)

    def test_zero_time_returns_nan(self) -> None:
        assert math.isnan(implied_volatility(1.0, s=100, k=100, t=0.0, r=0.04, option_type="call"))
