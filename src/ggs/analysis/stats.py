"""Statistical guardrails — log-odds, bootstrap CI, min-support, effect size (bd-9qw.5).

Provides rigorous statistical controls to prevent over-interpretation:

  1. Log-odds ratio with smoothing prior for group comparisons
  2. Bootstrap confidence intervals for density estimates
  3. Minimum support threshold to flag low-sample estimates
  4. Effect size (Cohen's d) for ranking meaningful differences

All outputs are explicitly labeled as "descriptive distinctiveness" —
never causal claims.

Reference: PLAN.md Section 5.3
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Any

from rich.console import Console

_console = Console()


# ---------------------------------------------------------------------------
# Support checking
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SupportCheck:
    """Result of checking if a sample has sufficient support.

    Attributes:
        sample_size: Number of observations.
        min_support: Minimum support threshold.
        sufficient: Whether sample_size >= min_support.
    """

    sample_size: int
    min_support: int
    sufficient: bool


def check_support(
    sample_size: int,
    *,
    min_support: int = 20,
) -> SupportCheck:
    """Check if a sample has sufficient observations for reporting.

    Density estimates based on fewer than ``min_support`` observations
    are flagged as low-support to prevent over-interpretation.

    Args:
        sample_size: Number of observations.
        min_support: Threshold below which estimates are unreliable.

    Returns:
        A :class:`SupportCheck` instance.
    """
    return SupportCheck(
        sample_size=sample_size,
        min_support=min_support,
        sufficient=sample_size >= min_support,
    )


# ---------------------------------------------------------------------------
# Log-odds ratio
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LogOddsResult:
    """Log-odds ratio result for group vs. background comparison.

    Attributes:
        group_label: Label identifying the group.
        group_count: Entity occurrences in the group.
        group_total: Total tokens in the group.
        background_count: Entity occurrences in background.
        background_total: Total tokens in background.
        log_odds: Smoothed log-odds ratio.
        smoothing_prior: The smoothing constant used.
        support: Support check for the group.
    """

    group_label: str
    group_count: int
    group_total: int
    background_count: int
    background_total: int
    log_odds: float
    smoothing_prior: float
    support: SupportCheck

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_label": self.group_label,
            "group_count": self.group_count,
            "group_total": self.group_total,
            "background_count": self.background_count,
            "background_total": self.background_total,
            "log_odds": round(self.log_odds, 6),
            "smoothing_prior": self.smoothing_prior,
            "sufficient_support": self.support.sufficient,
            "sample_size": self.support.sample_size,
        }


def compute_log_odds(
    group_label: str,
    group_count: int,
    group_total: int,
    background_count: int,
    background_total: int,
    *,
    smoothing_prior: float = 0.5,
    min_support: int = 20,
) -> LogOddsResult:
    """Compute smoothed log-odds ratio for a group vs. background.

    Uses additive (Laplace) smoothing to prevent infinite log-odds
    when an entity is unique to one group.

    Formula::

        odds_group = (group_count + prior) / (group_total - group_count + prior)
        odds_bg    = (bg_count + prior) / (bg_total - bg_count + prior)
        log_odds   = ln(odds_group / odds_bg)

    Args:
        group_label: Name of the group being compared.
        group_count: Entity occurrences in the group.
        group_total: Total tokens in the group.
        background_count: Entity occurrences in background.
        background_total: Total tokens in background.
        smoothing_prior: Additive smoothing constant.
        min_support: Minimum group_total for reliable estimates.

    Returns:
        A :class:`LogOddsResult`.
    """
    support = check_support(group_total, min_support=min_support)

    # Smoothed odds for group
    numerator_group = group_count + smoothing_prior
    denominator_group = (
        group_total - group_count + smoothing_prior
    )

    # Smoothed odds for background
    numerator_bg = background_count + smoothing_prior
    denominator_bg = (
        background_total - background_count + smoothing_prior
    )

    # Prevent division by zero
    if denominator_group <= 0 or denominator_bg <= 0:
        log_odds = 0.0
    else:
        odds_group = numerator_group / denominator_group
        odds_bg = numerator_bg / denominator_bg
        log_odds = 0.0 if odds_bg <= 0 else math.log(odds_group / odds_bg)

    return LogOddsResult(
        group_label=group_label,
        group_count=group_count,
        group_total=group_total,
        background_count=background_count,
        background_total=background_total,
        log_odds=log_odds,
        smoothing_prior=smoothing_prior,
        support=support,
    )


# ---------------------------------------------------------------------------
# Bootstrap confidence intervals
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BootstrapCI:
    """Bootstrap confidence interval for a density estimate.

    Attributes:
        point_estimate: The observed density.
        ci_lower: Lower bound of the confidence interval.
        ci_upper: Upper bound of the confidence interval.
        confidence_level: Confidence level (e.g. 0.95).
        n_samples: Number of bootstrap samples used.
        sample_size: Number of original observations.
        sufficient_support: Whether sample size meets min_support.
    """

    point_estimate: float
    ci_lower: float
    ci_upper: float
    confidence_level: float
    n_samples: int
    sample_size: int
    sufficient_support: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "point_estimate": round(self.point_estimate, 6),
            "ci_lower": round(self.ci_lower, 6),
            "ci_upper": round(self.ci_upper, 6),
            "confidence_level": self.confidence_level,
            "n_samples": self.n_samples,
            "sample_size": self.sample_size,
            "sufficient_support": self.sufficient_support,
        }

    @property
    def ci_width(self) -> float:
        """Width of the confidence interval (wider = less certain)."""
        return self.ci_upper - self.ci_lower


def bootstrap_density_ci(
    values: list[float],
    *,
    n_samples: int = 1000,
    confidence_level: float = 0.95,
    min_support: int = 20,
    rng: random.Random | None = None,
) -> BootstrapCI:
    """Compute bootstrap confidence interval for mean density.

    Resamples the values with replacement ``n_samples`` times, computes
    the mean for each resample, and returns the percentile CI.

    Args:
        values: Observed density values (one per line/observation).
        n_samples: Number of bootstrap resamples.
        confidence_level: Confidence level (default 0.95 for 95% CI).
        min_support: Minimum observations for reliable estimates.
        rng: Optional random.Random instance for reproducibility.

    Returns:
        A :class:`BootstrapCI` instance.
    """
    if rng is None:
        rng = random.Random()

    sample_size = len(values)
    support = check_support(sample_size, min_support=min_support)

    if sample_size == 0:
        return BootstrapCI(
            point_estimate=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            confidence_level=confidence_level,
            n_samples=n_samples,
            sample_size=0,
            sufficient_support=False,
        )

    point_estimate = statistics.mean(values)

    if sample_size == 1:
        return BootstrapCI(
            point_estimate=point_estimate,
            ci_lower=point_estimate,
            ci_upper=point_estimate,
            confidence_level=confidence_level,
            n_samples=n_samples,
            sample_size=1,
            sufficient_support=support.sufficient,
        )

    # Bootstrap resampling
    bootstrap_means: list[float] = []
    for _ in range(n_samples):
        resample = rng.choices(values, k=sample_size)
        bootstrap_means.append(statistics.mean(resample))

    bootstrap_means.sort()

    # Percentile method
    alpha = 1.0 - confidence_level
    lower_idx = math.floor(alpha / 2 * n_samples)
    upper_idx = math.ceil((1 - alpha / 2) * n_samples) - 1

    # Clamp indices
    lower_idx = max(0, min(lower_idx, n_samples - 1))
    upper_idx = max(0, min(upper_idx, n_samples - 1))

    return BootstrapCI(
        point_estimate=point_estimate,
        ci_lower=bootstrap_means[lower_idx],
        ci_upper=bootstrap_means[upper_idx],
        confidence_level=confidence_level,
        n_samples=n_samples,
        sample_size=sample_size,
        sufficient_support=support.sufficient,
    )


# ---------------------------------------------------------------------------
# Effect size (Cohen's d)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EffectSizeResult:
    """Cohen's d effect size for comparing two groups.

    Attributes:
        group_a_label: Label for group A.
        group_b_label: Label for group B.
        mean_a: Mean density of group A.
        mean_b: Mean density of group B.
        pooled_std: Pooled standard deviation.
        cohens_d: Cohen's d effect size.
        interpretation: Qualitative interpretation (negligible/small/medium/large).
    """

    group_a_label: str
    group_b_label: str
    mean_a: float
    mean_b: float
    pooled_std: float
    cohens_d: float
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_a_label": self.group_a_label,
            "group_b_label": self.group_b_label,
            "mean_a": round(self.mean_a, 6),
            "mean_b": round(self.mean_b, 6),
            "pooled_std": round(self.pooled_std, 6),
            "cohens_d": round(self.cohens_d, 6),
            "interpretation": self.interpretation,
        }


def _interpret_cohens_d(d: float) -> str:
    """Qualitative interpretation of Cohen's d magnitude.

    Uses conventional thresholds:
      < 0.2: negligible
      0.2-0.5: small
      0.5-0.8: medium
      > 0.8: large
    """
    d_abs = abs(d)
    if d_abs < 0.2:
        return "negligible"
    if d_abs < 0.5:
        return "small"
    if d_abs < 0.8:
        return "medium"
    return "large"


def compute_cohens_d(
    group_a_label: str,
    group_a_values: list[float],
    group_b_label: str,
    group_b_values: list[float],
) -> EffectSizeResult:
    """Compute Cohen's d effect size between two groups.

    Formula::

        d = (mean_a - mean_b) / pooled_std
        pooled_std = sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))

    Args:
        group_a_label: Name of group A.
        group_a_values: Density values for group A.
        group_b_label: Name of group B.
        group_b_values: Density values for group B.

    Returns:
        An :class:`EffectSizeResult`.
    """
    n_a = len(group_a_values)
    n_b = len(group_b_values)

    mean_a = statistics.mean(group_a_values) if n_a > 0 else 0.0
    mean_b = statistics.mean(group_b_values) if n_b > 0 else 0.0

    if n_a < 2 or n_b < 2:
        return EffectSizeResult(
            group_a_label=group_a_label,
            group_b_label=group_b_label,
            mean_a=mean_a,
            mean_b=mean_b,
            pooled_std=0.0,
            cohens_d=0.0,
            interpretation="negligible",
        )

    var_a = statistics.variance(group_a_values)
    var_b = statistics.variance(group_b_values)

    denom = n_a + n_b - 2
    if denom <= 0:
        pooled_std = 0.0
    else:
        pooled_var = (
            (n_a - 1) * var_a + (n_b - 1) * var_b
        ) / denom
        pooled_std = math.sqrt(pooled_var)

    cohens_d = 0.0 if pooled_std == 0.0 else (mean_a - mean_b) / pooled_std

    return EffectSizeResult(
        group_a_label=group_a_label,
        group_b_label=group_b_label,
        mean_a=mean_a,
        mean_b=mean_b,
        pooled_std=pooled_std,
        cohens_d=cohens_d,
        interpretation=_interpret_cohens_d(cohens_d),
    )
