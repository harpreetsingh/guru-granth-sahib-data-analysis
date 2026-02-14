"""Statistical guardrails tests (bd-9qw.5).

Tests minimum support checking, log-odds ratio with smoothing,
bootstrap confidence intervals, and Cohen's d effect size.
"""

from __future__ import annotations

import math
import random

from ggs.analysis.stats import (
    BootstrapCI,
    _interpret_cohens_d,
    bootstrap_density_ci,
    check_support,
    compute_cohens_d,
    compute_log_odds,
)

# ---------------------------------------------------------------------------
# Support check tests
# ---------------------------------------------------------------------------


class TestCheckSupport:
    """Tests for check_support."""

    def test_sufficient(self) -> None:
        result = check_support(50, min_support=20)
        assert result.sufficient is True
        assert result.sample_size == 50

    def test_insufficient(self) -> None:
        result = check_support(5, min_support=20)
        assert result.sufficient is False

    def test_exactly_threshold(self) -> None:
        result = check_support(20, min_support=20)
        assert result.sufficient is True

    def test_zero_sample(self) -> None:
        result = check_support(0, min_support=20)
        assert result.sufficient is False


# ---------------------------------------------------------------------------
# Log-odds tests
# ---------------------------------------------------------------------------


class TestComputeLogOdds:
    """Tests for compute_log_odds."""

    def test_equal_rates_zero_log_odds(self) -> None:
        """Same rate in group and background => log_odds ~ 0."""
        result = compute_log_odds(
            "test_group",
            group_count=10,
            group_total=100,
            background_count=100,
            background_total=1000,
        )
        assert abs(result.log_odds) < 0.1

    def test_higher_group_rate_positive(self) -> None:
        """Group has much higher rate => positive log_odds."""
        result = compute_log_odds(
            "test_group",
            group_count=50,
            group_total=100,
            background_count=10,
            background_total=1000,
        )
        assert result.log_odds > 0

    def test_lower_group_rate_negative(self) -> None:
        """Group has much lower rate => negative log_odds."""
        result = compute_log_odds(
            "test_group",
            group_count=1,
            group_total=100,
            background_count=500,
            background_total=1000,
        )
        assert result.log_odds < 0

    def test_smoothing_prevents_infinity(self) -> None:
        """Zero background count with smoothing should not produce inf."""
        result = compute_log_odds(
            "unique_group",
            group_count=10,
            group_total=100,
            background_count=0,
            background_total=1000,
        )
        assert math.isfinite(result.log_odds)

    def test_zero_group_with_smoothing(self) -> None:
        """Zero group count with smoothing should not produce -inf."""
        result = compute_log_odds(
            "absent_group",
            group_count=0,
            group_total=100,
            background_count=50,
            background_total=1000,
        )
        assert math.isfinite(result.log_odds)
        assert result.log_odds < 0

    def test_support_flagged(self) -> None:
        result = compute_log_odds(
            "small_group",
            group_count=1,
            group_total=5,
            background_count=100,
            background_total=1000,
            min_support=20,
        )
        assert result.support.sufficient is False

    def test_to_dict(self) -> None:
        result = compute_log_odds(
            "test", 10, 100, 50, 1000,
        )
        d = result.to_dict()
        assert "group_label" in d
        assert "log_odds" in d
        assert "sufficient_support" in d


# ---------------------------------------------------------------------------
# Bootstrap CI tests
# ---------------------------------------------------------------------------


class TestBootstrapDensityCI:
    """Tests for bootstrap_density_ci."""

    def test_empty_values(self) -> None:
        result = bootstrap_density_ci([])
        assert result.point_estimate == 0.0
        assert result.ci_lower == 0.0
        assert result.ci_upper == 0.0
        assert result.sufficient_support is False

    def test_single_value(self) -> None:
        result = bootstrap_density_ci([0.5])
        assert result.point_estimate == 0.5
        assert result.ci_lower == 0.5
        assert result.ci_upper == 0.5

    def test_ci_contains_point_estimate(self) -> None:
        rng = random.Random(42)
        values = [0.1, 0.2, 0.15, 0.18, 0.12, 0.22, 0.17,
                  0.19, 0.14, 0.16, 0.21, 0.13, 0.20, 0.11,
                  0.23, 0.15, 0.18, 0.16, 0.19, 0.17]
        result = bootstrap_density_ci(values, rng=rng)
        assert result.ci_lower <= result.point_estimate
        assert result.ci_upper >= result.point_estimate

    def test_ci_bounded(self) -> None:
        """CI should be within reasonable bounds."""
        rng = random.Random(42)
        values = [0.1, 0.2, 0.3] * 10
        result = bootstrap_density_ci(values, rng=rng)
        assert result.ci_lower >= 0.0
        assert result.ci_upper <= 1.0

    def test_wider_ci_for_small_sample(self) -> None:
        """Smaller sample => wider CI."""
        rng_small = random.Random(42)
        rng_large = random.Random(42)

        small = bootstrap_density_ci(
            [0.1, 0.2, 0.3], rng=rng_small,
        )
        large = bootstrap_density_ci(
            [0.1, 0.2, 0.3] * 20, rng=rng_large,
        )
        assert small.ci_width >= large.ci_width

    def test_deterministic_with_rng(self) -> None:
        """Same RNG seed produces same results."""
        values = [0.1, 0.2, 0.3, 0.4, 0.5] * 5
        r1 = bootstrap_density_ci(
            values, rng=random.Random(42),
        )
        r2 = bootstrap_density_ci(
            values, rng=random.Random(42),
        )
        assert r1.ci_lower == r2.ci_lower
        assert r1.ci_upper == r2.ci_upper

    def test_support_check(self) -> None:
        result = bootstrap_density_ci(
            [0.1, 0.2], min_support=20,
        )
        assert result.sufficient_support is False

        result2 = bootstrap_density_ci(
            [0.1] * 25, min_support=20,
        )
        assert result2.sufficient_support is True

    def test_to_dict(self) -> None:
        rng = random.Random(42)
        result = bootstrap_density_ci(
            [0.1, 0.2, 0.3] * 10, rng=rng,
        )
        d = result.to_dict()
        assert "point_estimate" in d
        assert "ci_lower" in d
        assert "ci_upper" in d
        assert "sufficient_support" in d

    def test_ci_width_property(self) -> None:
        ci = BootstrapCI(
            point_estimate=0.5,
            ci_lower=0.3,
            ci_upper=0.7,
            confidence_level=0.95,
            n_samples=1000,
            sample_size=100,
            sufficient_support=True,
        )
        assert abs(ci.ci_width - 0.4) < 1e-10


# ---------------------------------------------------------------------------
# Cohen's d tests
# ---------------------------------------------------------------------------


class TestComputeCohensD:
    """Tests for compute_cohens_d."""

    def test_identical_groups_zero_d(self) -> None:
        result = compute_cohens_d(
            "A", [0.1, 0.2, 0.3],
            "B", [0.1, 0.2, 0.3],
        )
        assert abs(result.cohens_d) < 1e-10

    def test_large_difference_large_d(self) -> None:
        result = compute_cohens_d(
            "high", [0.8, 0.9, 0.85, 0.88, 0.92],
            "low", [0.1, 0.15, 0.12, 0.08, 0.11],
        )
        assert result.interpretation == "large"

    def test_positive_d_when_a_higher(self) -> None:
        result = compute_cohens_d(
            "A", [0.5, 0.6, 0.7],
            "B", [0.1, 0.2, 0.3],
        )
        assert result.cohens_d > 0

    def test_negative_d_when_a_lower(self) -> None:
        result = compute_cohens_d(
            "A", [0.1, 0.2, 0.3],
            "B", [0.5, 0.6, 0.7],
        )
        assert result.cohens_d < 0

    def test_insufficient_data(self) -> None:
        result = compute_cohens_d(
            "A", [0.5],
            "B", [0.1, 0.2],
        )
        assert result.cohens_d == 0.0

    def test_to_dict(self) -> None:
        result = compute_cohens_d(
            "A", [0.1, 0.2, 0.3],
            "B", [0.4, 0.5, 0.6],
        )
        d = result.to_dict()
        assert "cohens_d" in d
        assert "interpretation" in d


class TestInterpretCohensD:
    """Tests for _interpret_cohens_d."""

    def test_negligible(self) -> None:
        assert _interpret_cohens_d(0.1) == "negligible"

    def test_small(self) -> None:
        assert _interpret_cohens_d(0.3) == "small"

    def test_medium(self) -> None:
        assert _interpret_cohens_d(0.6) == "medium"

    def test_large(self) -> None:
        assert _interpret_cohens_d(1.0) == "large"

    def test_negative_uses_absolute(self) -> None:
        assert _interpret_cohens_d(-1.0) == "large"
