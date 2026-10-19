# %% [markdown]
# # A/B Test: Moving the First Gate in Cookie Cats from Level 30 to Level 40
#
# **Decision to make:** Cookie Cats (a mobile puzzle game by Tactile Entertainment) forces players to wait or pay at a
# "gate". The team tested moving the first gate from level 30 (control, `gate_30`) to level 40 (treatment, `gate_40`).
# Should the change ship?
#
# * **Primary metric:** 7-day retention (did the player play 7 days after install?)
# * **Secondary metric:** 1-day retention
# * **Guardrail:** game rounds played in the first 14 days
#
# Plan: sanity checks (sample ratio mismatch, duplicates, outliers), power and minimum detectable effect, frequentist
# two-proportion z-tests with confidence intervals, a permutation test, a Bayesian analysis, segment checks with
# multiple-testing correction, then a one-page decision memo.

# %%
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
from abtest import (beta_binomial, mde_two_proportions, power_two_proportions,  # noqa: E402
                    sample_size_two_proportions, srm_test, two_proportion_ztest)

FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid", context="notebook")
C30, C40 = "#1f4e79", "#e07b39"
SEED = 42
stats_out = {}

def savefig(fig, name):
    fig.tight_layout(); fig.savefig(FIG / name, dpi=150, bbox_inches="tight"); plt.show()

df = pd.read_csv(ROOT / "data" / "raw" / "cookie_cats.csv")
df.head()

# %% [markdown]
# ## 1. Sanity checks

# %%
print("Rows:", len(df), "| duplicate user IDs:", df["userid"].duplicated().sum(), "| missing values:", int(df.isna().sum().sum()))
counts = df["version"].value_counts().sort_index()
print(counts, "\nShare in gate_30:", round(counts["gate_30"] / len(df), 4))
chi2, p_srm = srm_test(counts["gate_30"], counts["gate_40"])
print(f"Sample ratio mismatch test (planned 50/50): chi2 = {chi2:.2f}, p = {p_srm:.4f}")
stats_out.update(n_players=len(df), n_gate30=int(counts["gate_30"]), n_gate40=int(counts["gate_40"]),
                 share_gate30=round(counts["gate_30"] / len(df) * 100, 2), srm_chi2=round(chi2, 2), srm_p=round(p_srm, 4))

# %% [markdown]
# **The SRM check fails at the 1% level** (p below 0.01): gate_40 has 789 more players than a fair 50/50 split would
# typically produce. The imbalance is small (49.6% vs 50.4%) but it is more than chance would usually create, so it
# could indicate a bucketing or logging problem. The data has no install timestamps or platform fields to diagnose it,
# so the results below are reported with this caveat and the memo asks engineering to check assignment.

# %%
print(df["sum_gamerounds"].describe(percentiles=[.5, .9, .99, .999]).round(1))
top = df.nlargest(3, "sum_gamerounds")
print(top)
fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
axes[0].boxplot([df.loc[df.version == v, "sum_gamerounds"] for v in ["gate_30", "gate_40"]], tick_labels=["gate_30", "gate_40"])
axes[0].set(title="Game rounds in 14 days (raw): one extreme outlier", yscale="log", ylabel="rounds (log scale)")
clipped = df[df["sum_gamerounds"] <= 200]
sns.histplot(data=clipped, x="sum_gamerounds", hue="version", bins=100, element="step", stat="density",
             common_norm=False, palette={"gate_30": C30, "gate_40": C40}, ax=axes[1])
axes[1].set(title="Distribution of rounds played (players with <= 200 rounds)")
savefig(fig, "01_gamerounds_distribution.png")
zero = (df["sum_gamerounds"] == 0).mean()
stats_out["max_rounds"] = int(df["sum_gamerounds"].max()); stats_out["second_max_rounds"] = int(top.iloc[1]["sum_gamerounds"])
stats_out["share_zero_rounds"] = round(zero * 100, 1)
stats_out["share_reached_30"] = round((df["sum_gamerounds"] >= 30).mean() * 100, 1)
print(f"{zero:.1%} of players installed but never played a round; {stats_out['share_reached_30']}% played 30+ rounds")

# %% [markdown]
# One player logged **49,854 rounds in 14 days** (about 2.5 rounds a minute, non-stop): almost certainly a bot or a
# logging error. It does not affect the retention metrics (each player counts once) but would distort the mean of the
# rounds guardrail, so it is excluded from that metric only. Nearly 4.4% of players never played a round, which is
# normal for mobile installs and identical in both groups.

# %% [markdown]
# ## 2. Power and minimum detectable effect
# Before reading results: was the test big enough to detect a meaningful change?

# %%
n_min = int(counts.min())
base7, base1 = df.loc[df.version == "gate_30", "retention_7"].mean(), df.loc[df.version == "gate_30", "retention_1"].mean()
mde7, mde1 = mde_two_proportions(base7, n_min), mde_two_proportions(base1, n_min)
print(f"With {n_min:,} players per group (alpha 0.05, power 80%):")
print(f"  7-day retention baseline {base7:.2%}: MDE = {mde7*100:.2f} pp ({mde7/base7:.1%} relative)")
print(f"  1-day retention baseline {base1:.2%}: MDE = {mde1*100:.2f} pp ({mde1/base1:.1%} relative)")
need_05 = sample_size_two_proportions(base7, -0.005)
print(f"  Players per group needed to detect a 0.5 pp change in 7-day retention: {need_05:,}")
stats_out.update(mde7_pp=round(mde7 * 100, 2), mde1_pp=round(mde1 * 100, 2), n_needed_05pp=need_05)

diffs = np.linspace(0.001, 0.02, 100)
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(diffs * 100, [power_two_proportions(base7, -d, n_min) for d in diffs], color=C30, label="7-day retention")
ax.plot(diffs * 100, [power_two_proportions(base1, -d, n_min) for d in diffs], color=C40, label="1-day retention")
ax.axhline(0.8, ls="--", color="grey", lw=1); ax.axvline(mde7 * 100, ls=":", color=C30, lw=1)
ax.set(title=f"Power of this test ({n_min:,} players per group)", xlabel="True absolute difference (percentage points)", ylabel="Power")
ax.legend(); savefig(fig, "02_power_curve.png")

# %% [markdown]
# ## 3. Results: frequentist two-proportion z-tests

# %%
rows = []
for metric in ["retention_1", "retention_7"]:
    a = df.loc[df.version == "gate_30", metric]; b = df.loc[df.version == "gate_40", metric]
    r = two_proportion_ztest(int(a.sum()), len(a), int(b.sum()), len(b))
    rows.append({"metric": metric, "gate_30": r.p_a, "gate_40": r.p_b, "diff_pp": r.diff * 100,
                 "ci95_low_pp": r.ci_low * 100, "ci95_high_pp": r.ci_high * 100, "relative_change_pct": r.rel_lift * 100,
                 "z": r.z, "p_value": r.p_value})
res = pd.DataFrame(rows)
res.round({c: 5 for c in res.columns if c != "p_value"}).to_csv(RES / "frequentist_results.csv", index=False)
stats_out["frequentist"] = res.round(5).to_dict("records")
res.round(4)

# %%
# Permutation test for the primary metric (no distributional assumptions): shuffle group labels 10,000 times
rng = np.random.default_rng(SEED)
y7 = df["retention_7"].to_numpy(); is40 = (df["version"] == "gate_40").to_numpy()
obs = y7[is40].mean() - y7[~is40].mean()
perm = np.empty(10_000)
for i in range(len(perm)):
    s = rng.permutation(is40); perm[i] = y7[s].mean() - y7[~s].mean()
p_perm = (np.abs(perm) >= abs(obs)).mean()
print(f"Observed 7-day difference {obs*100:.2f} pp; permutation p = {p_perm:.4f} ({(np.abs(perm) >= abs(obs)).sum()} of 10,000 shuffles as extreme)")
stats_out["perm_p_retention7"] = float(p_perm)

# Guardrail: game rounds (outlier removed). Mann-Whitney U and bootstrap CI for the difference in means
g = df[df["sum_gamerounds"] < 10_000]
r30, r40 = g.loc[g.version == "gate_30", "sum_gamerounds"].to_numpy(), g.loc[g.version == "gate_40", "sum_gamerounds"].to_numpy()
u, p_mw = stats.mannwhitneyu(r30, r40, alternative="two-sided")
boot = [rng.choice(r40, len(r40)).mean() - rng.choice(r30, len(r30)).mean() for _ in range(2000)]
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"Rounds: mean {r30.mean():.2f} vs {r40.mean():.2f}, diff {r40.mean()-r30.mean():.2f} (95% CI {lo:.2f} to {hi:.2f}); "
      f"median {np.median(r30):.0f} vs {np.median(r40):.0f}; Mann-Whitney p = {p_mw:.4f}")
stats_out["rounds"] = {"mean_30": round(r30.mean(), 2), "mean_40": round(r40.mean(), 2), "diff": round(r40.mean() - r30.mean(), 2),
                       "ci": [round(lo, 2), round(hi, 2)], "median_30": float(np.median(r30)), "median_40": float(np.median(r40)),
                       "mannwhitney_p": round(float(p_mw), 4)}

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
for ax, metric, title in [(axes[0], "retention_1", "1-day retention"), (axes[1], "retention_7", "7-day retention")]:
    s = df.groupby("version")[metric].agg(["mean", "count"])
    se = np.sqrt(s["mean"] * (1 - s["mean"]) / s["count"])
    ax.bar(s.index, s["mean"] * 100, yerr=1.96 * se * 100, capsize=8, color=[C30, C40])
    for i, v in enumerate(s["mean"] * 100): ax.text(i, v / 2, f"{v:.2f}%", ha="center", color="white", fontsize=13, weight="bold")
    row = res[res.metric == metric].iloc[0]
    ax.set(title=f"{title}: {row.diff_pp:+.2f} pp (95% CI {row.ci95_low_pp:+.2f} to {row.ci95_high_pp:+.2f}), p = {row.p_value:.4f}", ylabel="% of players")
    ax.title.set_fontsize(10)
savefig(fig, "03_retention_by_group.png")

# %% [markdown]
# ## 4. Bayesian analysis
# Uniform Beta(1, 1) priors; 200,000 posterior draws. This answers the question stakeholders actually ask: *how likely
# is it that gate_40 is worse, and how much retention do we risk by choosing it?*

# %%
bayes = {}
fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
for ax, metric in zip(axes, ["retention_1", "retention_7"]):
    a = df.loc[df.version == "gate_30", metric]; b = df.loc[df.version == "gate_40", metric]
    bb = beta_binomial(int(a.sum()), len(a), int(b.sum()), len(b), seed=SEED)
    d = (bb["samples_b"] - bb["samples_a"]) * 100
    sns.kdeplot(d, fill=True, color=C40, ax=ax); ax.axvline(0, color="k", lw=1)
    ax.set(title=f"{metric}: posterior of gate_40 minus gate_30\nP(gate_30 better) = {1 - bb['prob_b_better']:.4f}",
           xlabel="Difference (percentage points)")
    bayes[metric] = {"prob_gate30_better": round(1 - bb["prob_b_better"], 4),
                     "expected_loss_choose_gate40_pp": round(bb["expected_loss_choose_b"] * 100, 4),
                     "expected_loss_choose_gate30_pp": round(bb["expected_loss_choose_a"] * 100, 4),
                     "credible_interval_pp": [round(x * 100, 3) for x in bb["diff_ci"]]}
savefig(fig, "04_bayesian_posterior.png")
stats_out["bayesian"] = bayes
pd.DataFrame(bayes).T

# %% [markdown]
# ## 5. Segment checks
# Did the effect differ by engagement? Segments are defined by **rounds played**, which is itself measured after
# assignment and can be influenced by the gate. These are exploratory checks, not causal subgroup effects, and p-values
# are Holm-corrected for the number of comparisons.

# %%
bins = [-1, 0, 9, 29, 39, 99, np.inf]
labels = ["0 rounds", "1-9", "10-29", "30-39", "40-99", "100+"]
df["engagement"] = pd.cut(df["sum_gamerounds"], bins=bins, labels=labels)
seg_rows = []
for seg_name, sub in df.groupby("engagement", observed=True):
    a = sub[sub.version == "gate_30"]; b = sub[sub.version == "gate_40"]
    r = two_proportion_ztest(int(a.retention_7.sum()), len(a), int(b.retention_7.sum()), len(b))
    seg_rows.append({"segment": seg_name, "n_gate30": len(a), "n_gate40": len(b), "ret7_gate30": r.p_a * 100, "ret7_gate40": r.p_b * 100,
                     "diff_pp": r.diff * 100, "ci_low_pp": r.ci_low * 100, "ci_high_pp": r.ci_high * 100, "p_value": r.p_value})
seg = pd.DataFrame(seg_rows)
seg["p_holm"] = multipletests(seg["p_value"], method="holm")[1]
# Share of each group in each engagement band (does the gate change how far people play?)
seg["share_gate30_pct"] = seg["n_gate30"] / seg["n_gate30"].sum() * 100
seg["share_gate40_pct"] = seg["n_gate40"] / seg["n_gate40"].sum() * 100
rnd = {c: 4 for c in seg.columns if c not in ("p_value", "p_holm", "segment")}
seg.round(rnd).to_csv(RES / "segment_results.csv", index=False)
stats_out["segments"] = seg.round(rnd).to_dict("records")
seg.round(3)

# %%
fig, ax = plt.subplots(figsize=(10, 4.8))
y = np.arange(len(seg))
ax.errorbar(seg["diff_pp"], y, xerr=[seg["diff_pp"] - seg["ci_low_pp"], seg["ci_high_pp"] - seg["diff_pp"]], fmt="o", color=C40, capsize=4)
ax.axvline(0, color="k", lw=1)
ax.set_yticks(y, [f"{s} (n={a + b:,})" for s, a, b in zip(seg.segment, seg.n_gate30, seg.n_gate40)])
ax.set(title="7-day retention difference (gate_40 minus gate_30) by rounds played, 95% CI", xlabel="percentage points")
savefig(fig, "05_segment_effects.png")

# %%
with open(RES / "summary_stats.json", "w") as f:
    json.dump(stats_out, f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(stats_out, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
