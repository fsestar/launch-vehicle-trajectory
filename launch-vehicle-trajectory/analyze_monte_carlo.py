"""Analyse the Monte Carlo results and save the summary figure to figures/."""
import csv
import os

import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(HERE, "monte_carlo_results.csv")
OUTPUT_PNG = os.path.join(HERE, "figures", "mc_analysis.png")

# nominal design values (must match monte_carlo.py)
M_DOT1 = 7.80
V_EXHAUST1 = 2770.0
DRY1, FUEL1 = 40.0, 760.0
DRY2, FUEL2 = 8.0, 200.0
PAYLOAD = 20.0
KICK_NOMINAL = 8.0
G = 9.81


def wilson_interval(k, n, z=1.96):
    """95 % Wilson confidence interval for a proportion k/n. Valid also near 0 % and 100 %."""
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2*n)) / denom
    half = z * np.sqrt(p*(1 - p)/n + z**2/(4*n**2)) / denom
    return center - half, center + half


def main():
    with open(INPUT_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    def col(name):
        return np.array([float(r[name]) for r in rows])

    outcome = np.array([r["outcome"] for r in rows])
    is_success = outcome == "success"
    is_crashed = outcome == "crashed"

    thrust1 = M_DOT1 * col("f_thrust1") * V_EXHAUST1
    total_mass = (PAYLOAD + DRY1 * col("f_dry1") + FUEL1 * col("f_fuel1")
                  + DRY2 * col("f_dry2") + FUEL2 * col("f_fuel2"))
    twr0 = thrust1 / (total_mass * G)
    nominal_mass = PAYLOAD + DRY1 + FUEL1 + DRY2 + FUEL2
    nominal_twr = M_DOT1 * V_EXHAUST1 / (nominal_mass * G)

    variables = {
        "f_thrust1": col("f_thrust1"), "f_thrust2": col("f_thrust2"),
        "f_dry1": col("f_dry1"), "f_fuel1": col("f_fuel1"),
        "f_dry2": col("f_dry2"), "f_fuel2": col("f_fuel2"),
        "f_cd": col("f_cd"), "kick_deg": col("kick_deg"),
        "TWR0 (derived)": twr0,
    }

    n = len(rows)
    k = int(is_success.sum())
    lo, hi = wilson_interval(k, n)
    print(f"flights: {n}")
    print(f"success rate: {100*k/n:.1f}%  (Wilson 95% interval: {100*lo:.1f}% to {100*hi:.1f}%)")
    for name in ["success", "crashed", "low_orbit", "never_circularized"]:
        count = int((outcome == name).sum())
        if count:
            print(f"  {name:20s} {count:4d}  ({100*count/n:.1f}%)")
    print(f"nominal TWR: {nominal_twr:.4f}")
    print()

    print("variable            | mean (success) | mean (crashed) | effect size d")
    effects = []
    for name, values in variables.items():
        s, c = values[is_success], values[is_crashed]
        if len(s) < 2 or len(c) < 2:
            continue
        pooled = np.sqrt((s.var(ddof=1) + c.var(ddof=1)) / 2)
        d = (s.mean() - c.mean()) / pooled
        effects.append((abs(d), name, s.mean(), c.mean(), d))
    for _, name, ms, mc, d in sorted(effects, reverse=True):
        print(f"{name:19s} | {ms:14.4f} | {mc:14.4f} | {d:+.2f}")

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    apogee = col("apogee_km")[is_success]
    axes[0].hist(apogee, bins=20, color="steelblue", edgecolor="white")
    axes[0].set_xlabel("Final orbit altitude (km)")
    axes[0].set_ylabel("Number of flights")
    axes[0].set_title("Orbit altitude of successful flights")
    axes[0].grid(True, alpha=0.3)

    edges = np.quantile(twr0, np.linspace(0, 1, 9))
    centers, rates, counts = [], [], []
    for lo_e, hi_e in zip(edges[:-1], edges[1:]):
        mask = (twr0 >= lo_e) & (twr0 <= hi_e)
        centers.append(twr0[mask].mean())
        rates.append(100 * is_success[mask].mean())
        counts.append(mask.sum())
    axes[1].plot(centers, rates, "o-", color="darkgreen")
    axes[1].axvline(nominal_twr, color="gray", linestyle="--", label="nominal TWR")
    axes[1].set_xlabel("Liftoff thrust-to-weight ratio")
    axes[1].set_ylabel("Success rate (%)")
    axes[1].set_title(f"Success rate vs TWR ({counts[0]} flights per bin)")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    colors = {"success": "green", "crashed": "red", "low_orbit": "orange",
              "never_circularized": "purple"}
    for name, color in colors.items():
        mask = outcome == name
        if mask.any():
            axes[2].scatter(twr0[mask], col("kick_deg")[mask], s=18, c=color,
                            label=name, alpha=0.7)
    axes[2].scatter([nominal_twr], [KICK_NOMINAL], marker="*", s=200, c="black", label="nominal")
    axes[2].set_xlabel("Liftoff thrust-to-weight ratio")
    axes[2].set_ylabel("Kick angle (deg)")
    axes[2].set_title("Outcome in (TWR, kick angle) space")
    axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.3)

    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=100)
    print(f"\nfigure saved to {OUTPUT_PNG}")
    plt.show()


if __name__ == "__main__":
    main()