import sys
from pathlib import Path

import numpy as np
import pytest
from statsmodels.stats.proportion import proportions_ztest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from abtest import (beta_binomial, mde_two_proportions, power_two_proportions,  # noqa: E402
                    sample_size_two_proportions, srm_test, two_proportion_ztest)


def test_ztest_matches_statsmodels():
    r = two_proportion_ztest(500, 5000, 560, 5000)
    z, p = proportions_ztest([560, 500], [5000, 5000])
    assert r.z == pytest.approx(z)
    assert r.p_value == pytest.approx(p)
    assert r.ci_low < r.diff < r.ci_high


def test_srm_balanced_and_unbalanced():
    assert srm_test(5000, 5000)[1] == pytest.approx(1.0)
    assert srm_test(5000, 5400)[1] < 0.001


def test_mde_and_sample_size_are_consistent():
    n = sample_size_two_proportions(0.19, 0.01)
    assert power_two_proportions(0.19, 0.01, n) == pytest.approx(0.8, abs=0.01)
    assert mde_two_proportions(0.19, n) == pytest.approx(0.01, rel=0.05)


def test_bayes_obvious_winner():
    r = beta_binomial(100, 1000, 200, 1000, draws=50_000)
    assert r["prob_b_better"] > 0.999
    assert r["expected_loss_choose_b"] < 1e-4
