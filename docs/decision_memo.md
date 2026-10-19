# Decision memo: keep the first gate at level 30

**To:** Cookie Cats product team · **From:** Anthony Adusei-Poku, Data Analyst · **Re:** Gate 30 vs gate 40 A/B test

## Recommendation
**Do not move the first gate to level 40. Keep it at level 30.** Before the next test, ask engineering to check
how players are assigned to groups, because the groups are slightly unbalanced.

## What we tested
90,189 new players were randomly assigned at install: 44,700 to the current gate at level 30 and 45,489 to a gate
at level 40. The primary metric was 7-day retention. 1-day retention and rounds played were secondary and guardrail
metrics.

## Results

| Metric | Gate 30 | Gate 40 | Difference (95% CI) | p-value |
|---|---:|---:|---:|---:|
| **7-day retention (primary)** | **19.02%** | **18.20%** | **-0.82 pp (-1.33 to -0.31)** | **0.0016** |
| 1-day retention | 44.82% | 44.23% | -0.59 pp (-1.24 to +0.06) | 0.074 |
| Mean rounds in 14 days* | 51.34 | 51.30 | -0.04 (-1.36 to +1.27) | 0.051 (Mann-Whitney) |

\* one player with 49,854 rounds (almost certainly a bot or logging error) excluded.

* Moving the gate **reduced 7-day retention by 0.82 percentage points, a 4.3% relative drop**. That is roughly
  **820 fewer players still playing after a week for every 100,000 installs**.
* The result holds up four ways: z-test p = 0.0016, permutation test p = 0.0017, the 95% interval excludes zero,
  and the Bayesian analysis gives a **99.9% probability that gate 30 is better**. Choosing gate 40 risks an expected
  0.82 pp of 7-day retention; choosing gate 30 risks almost nothing (0.0001 pp).
* The test was well powered: it could detect a change of 0.74 pp in 7-day retention with 80% power, and the observed
  effect is larger than that.
* 1-day retention and rounds played show no significant change, so the damage shows up after the first day.
  A plausible reason is that an earlier gate forces a break that keeps the game feeling fresh, while a later gate
  lets players burn through content and lose interest.
* The largest drop is among players who played 40 to 99 rounds (32.9% vs 29.4% retained, -3.5 pp, Holm-adjusted
  p < 0.001). This is exactly where gate-40 players meet their first gate. Rounds played is measured after
  assignment, so this is a clue, not proof.

## Caveat
The split is 49.6% / 50.4% instead of 50/50. A sample ratio mismatch test gives p = 0.009, which suggests a
possible problem with assignment or logging (for example, one app version or platform tracked differently). The
imbalance is small and the effect is consistent across every method, so the recommendation stands. Still, the
assignment pipeline should be checked before further gate tests are trusted.

## Next steps
1. Keep gate 30 for all players.
2. Engineering: investigate the sample ratio mismatch (assignment logs by date, platform and app version).
3. Consider testing an **earlier** gate (for example level 25), since a later gate hurt retention, with revenue
   from gate purchases tracked as a co-primary metric.
