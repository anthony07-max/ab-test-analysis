"""Small, tested statistics helpers for A/B test analysis."""
from dataclasses import dataclass

import numpy as np
from scipy import stats


def srm_test(n_a: int, n_b: int, expected_share_a: float = 0.5):
    """Sample ratio mismatch: chi-square goodness-of-fit of observed group sizes vs the planned split."""
    n = n_a + n_b
    expected = np.array([n * expected_share_a, n * (1 - expected_share_a)])
    chi2, p = stats.chisquare([n_a, n_b], expected)
    return float(chi2), float(p)


@dataclass
class PropTest:
    p_a: float
    p_b: float
    diff: float          # p_b - p_a (absolute, proportion units)
    ci_low: float
    ci_high: float
    rel_lift: float      # diff / p_a
    z: float
    p_value: float


def two_proportion_ztest(x_a: int, n_a: int, x_b: int, n_b: int, alpha: float = 0.05) -> PropTest:
    """Two-sided z-test for p_b - p_a (pooled SE for the test, unpooled SE for the Wald CI)."""
    p_a, p_b = x_a / n_a, x_b / n_b
    pooled = (x_a + x_b) / (n_a + n_b)
    se_pooled = np.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    z = (p_b - p_a) / se_pooled
    p_value = 2 * stats.norm.sf(abs(z))
    se = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    zc = stats.norm.ppf(1 - alpha / 2)
    d = p_b - p_a
    return PropTest(p_a, p_b, d, d - zc * se, d + zc * se, d / p_a, float(z), float(p_value))


def mde_two_proportions(p_base: float, n_per_group: int, alpha: float = 0.05, power: float = 0.8) -> float:
    """Minimum detectable absolute difference for a two-sided test with equal group sizes."""
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    return float((za + zb) * np.sqrt(2 * p_base * (1 - p_base) / n_per_group))


def sample_size_two_proportions(p_base: float, abs_diff: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Players needed per group to detect an absolute difference (normal approximation)."""
    p2 = p_base + abs_diff
    za, zb = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    pbar = (p_base + p2) / 2
    n = (za * np.sqrt(2 * pbar * (1 - pbar)) + zb * np.sqrt(p_base * (1 - p_base) + p2 * (1 - p2))) ** 2 / abs_diff ** 2
    return int(np.ceil(n))


def power_two_proportions(p_base: float, abs_diff: float, n_per_group: int, alpha: float = 0.05) -> float:
    za = stats.norm.ppf(1 - alpha / 2)
    p2 = p_base + abs_diff
    se = np.sqrt(p_base * (1 - p_base) / n_per_group + p2 * (1 - p2) / n_per_group)
    return float(stats.norm.sf(za - abs(abs_diff) / se) + stats.norm.cdf(-za - abs(abs_diff) / se))


def beta_binomial(x_a, n_a, x_b, n_b, draws=200_000, seed=0, prior=(1, 1)):
    """Posterior samples of each group's rate under a Beta prior; returns P(B > A) and expected loss."""
    rng = np.random.default_rng(seed)
    a = rng.beta(prior[0] + x_a, prior[1] + n_a - x_a, draws)
    b = rng.beta(prior[0] + x_b, prior[1] + n_b - x_b, draws)
    return {
        "samples_a": a, "samples_b": b,
        "prob_b_better": float((b > a).mean()),
        "expected_loss_choose_b": float(np.maximum(a - b, 0).mean()),
        "expected_loss_choose_a": float(np.maximum(b - a, 0).mean()),
        "diff_ci": tuple(np.percentile(b - a, [2.5, 97.5]).tolist()),
    }
